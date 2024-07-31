import logging
import socket
import time
from datetime import datetime

import mysql.connector
import schedule
import configparser

conf = configparser.ConfigParser()  # 配置读取类实例化
conf.read('./config.ini', encoding="utf8")  # 读取.ini文件

# 配置日志输出到文件
logging.basicConfig(filename='./logfile.log',
                    level=logging.ERROR,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 配置连接池
dbconfig = {
    "host": conf.get("mysql", "host"),
    "port": conf.getint("mysql", "port"),
    "user": conf.get("mysql", "user"),
    "password": conf.get("mysql", "password"),
    "database": conf.get("mysql", "db"),
    "auth_plugin": conf.get("mysql", "auth_plugin")
}

meter_address = conf.get("meter", "address")
meter_h6000_port = conf.getint("meter", "h6000_port")
meter_nhm6300_port = conf.getint("meter", "nhm6300_port")
meter_h8000_port = conf.getint("meter", "h8000_port")

temperature_humidity_sensors_address = conf.get("temperature_humidity_sensors", "address")
temperature_humidity_sensors_port = conf.getint("temperature_humidity_sensors", "port")

pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,  # 连接池的大小，可以根据实际情况调整
    **dbconfig
)


def get_connection():
    """
    使用连接池获取连接
    """
    return pool.get_connection()


def release_connection(connection):
    """
    归还连接到连接池
    """
    connection.close()  # close() 方法会把连接返回给连接池


def get_temp_and_humidity(ip=temperature_humidity_sensors_address, port=temperature_humidity_sensors_port):
    """
    获取温湿度数据
    :param ip: TCP连接的ip地址
    :param port: TCP连接的port端口
    :return: 温度，湿度
    """
    # 创建一个socket对象
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # 连接到目标IP和端口
        sock.connect((ip, port))

        # 定义请求数据
        request = b'\x01\x03\x02\x00\x00\x02\xC5\xB3'

        # 发送请求数据
        sock.sendall(request)

        # 接收响应数据
        response = sock.recv(18)  # 接收缓冲区大小
        # print(response)
        if len(response) >= 9:
            # 解析响应数据
            temp = int.from_bytes(response[3:5], byteorder='big') / 10
            humidity = int.from_bytes(response[5:7], byteorder='big') / 10
            # x = int.from_bytes(response[7:9], byteorder='big') / 10

    # print("温度：", temp)
    # print("湿度：", humidity)  # [5:7]是当前总有功电能  得除100
    return (round(temp, 2), round(humidity, 2))


def get_electricity(ip=meter_address, port=23):
    """
    通过TCP连接某个电表，获取电量
    :param ip: TCP连接的ip地址
    :param port: TCP连接的port端口，根据端口的不同区分不同电表
    :return: 总有功电能（电量）kw*h
    """
    request = ''
    NHM6300_request = b'\x02\x04\x00\x1D\x00\x02\xE1\xFE'
    H6000_request = b'\x04\x04\x00\x1D\x00\x02\xE1\x98'
    H8000_request = b'\x03\x04\x00\x1D\x00\x02\xE0\x2F'
    # 创建一个socket对象
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # 连接到目标IP和端口
        sock.connect((ip, port))

        # 定义请求数据
        if port == meter_nhm6300_port:
            request = NHM6300_request
        elif port == meter_h6000_port:
            request = H6000_request
        elif port == meter_h8000_port:
            request = H8000_request
        # request = b'\x01\x03\x02\x00\x00\x02\xC5\xB3'

        # 发送请求数据
        sock.sendall(request)

        # 接收响应数据
        response = sock.recv(18)  # 接收缓冲区大小
        # print(response)
        if len(response) >= 9:
            # 解析响应数据
            # temp = int.from_bytes(response[3:5], byteorder='big') / 10
            electricity = int.from_bytes(response[5:7], byteorder='big') / 100
            # x = int.from_bytes(response[7:9], byteorder='big') / 10

    # print("总有功电能：", electricity)  # [5:7]是当前总有功电能  得除100
    return electricity


def get_total_electricity():
    total = 0

    total += get_electricity(port=meter_nhm6300_port)
    total += get_electricity(port=meter_h6000_port)
    total += get_electricity(port=meter_h8000_port)
    return round(total, 2)


# 插入数据到数据库
def insert_data(table_name, data):
    conn = get_connection()
    cursor = conn.cursor()
    create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if table_name == 'temperature':
            cursor.execute("INSERT INTO temperature (temperature, create_time) VALUES (%s, %s)",
                           (data[0], create_time))
            print(f"采集到温度：{data[0]}")
        elif table_name == 'humidity':
            cursor.execute("INSERT INTO humidity (humidity, create_time) VALUES (%s, %s)", (data[1], create_time))
            print(f"采集到湿度：{data[1]}")
        elif table_name == 'electricity':
            cursor.execute("INSERT INTO electricity (electricity, create_time) VALUES (%s, %s)", (data, create_time))
            print(f"采集到总用电量：{data}")
        conn.commit()
    finally:
        release_connection(conn)  # 确保连接总是被归还到连接池


# 主函数，用于调度和执行任务
def main():
    # 创建数据库连接
    conn = get_connection()

    # 创建表格（如果不存在）
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS temperature (
                id INT AUTO_INCREMENT PRIMARY KEY,
                temperature FLOAT(10,2),
                create_time DATETIME
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS humidity (
                id INT AUTO_INCREMENT PRIMARY KEY,
                humidity FLOAT(10,2),
                create_time DATETIME
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS electricity (
                id INT AUTO_INCREMENT PRIMARY KEY,
                electricity FLOAT(10,2),
                create_time DATETIME
            )
        ''')
        conn.commit()
    finally:
        release_connection(conn)

    # 定时任务
    # schedule.every(1).minutes.do(get_temp_and_humidity)
    schedule.every(1).minutes.do(lambda: insert_data('temperature', get_temp_and_humidity()))
    schedule.every(1).minutes.do(lambda: insert_data('humidity', get_temp_and_humidity()))
    schedule.every(1).minutes.do(lambda: insert_data('electricity', get_total_electricity()))

    # 电表数据获取和存储
    # for ip, port in [('192.168.18.236', 23), ('192.168.18.237', 26), ('192.168.18.238', 29)]:
    #     schedule.every(1).minutes.do(
    #         lambda ip=ip, port=port: insert_data(conn, 'electricity', get_electricity(ip, port)))

    # schedule 模块本身并不自动启动任务，你需要在一个循环中调用 schedule.run_pending() 方法来检查是否有待执行的任务，通常这个检查会在一个无限循环中进行
    while True:
        schedule.run_pending()
        time.sleep(1)


# print(get_temp_and_humidity()[0], " ----------- ", get_temp_and_humidity()[1])
# get_electricity(port=NHM6300_port)
# get_electricity(port=H6000_port)
# get_electricity(port=H8000_port)
# print(get_total_electricity())

print("=================== 开始采集 ===================")
main()
# thread = threading.Thread(target=main)
# thread.start()
