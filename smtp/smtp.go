package service

import (
	"cmall/model"
	"os"
	"strings"
	"time"

	"github.com/dgrijalva/jwt-go"
	"gopkg.in/mail.v2"
)

// 加密密钥
var jwtSecret = []byte(os.Getenv("JWT_SECRET"))

// EmailClaims ...
type EmailClaims struct {
	UserID        uint   `json:"user_id"`
	Email         string `json:"email"`
	Password      string `json:"password"`
	OperationType uint   `json:"operation_type"`
	jwt.StandardClaims
}

// SendEmailService 发送邮件的服务
type SendEmailService struct {
	UserID   uint   `form:"user_id" json:"user_id"`
	Email    string `form:"email" json:"email"`
	Password string `form:"password" json:"password"`
	//OpertionType 1:绑定邮箱 2：解绑邮箱 3：改密码
	OperationType uint `form:"operation_type" json:"operation_type"`
}

// GenerateEmailToken 签发邮箱验证Token
func GenerateEmailToken(userID, Operation uint, email, password string) (string, error) {
	nowTime := time.Now()
	expireTime := nowTime.Add(15 * time.Minute)

	claims := EmailClaims{
		userID,
		email,
		password,
		Operation,
		jwt.StandardClaims{
			ExpiresAt: expireTime.Unix(),
			Issuer:    "cmall",
		},
	}

	tokenClaims := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	token, err := tokenClaims.SignedString(jwtSecret)

	return token, err
}

// Send 发送邮件
func (service *SendEmailService) Send() {
	// 定义验证链接地址
	var address string

	// 通知结构体，用于获取通知消息
	var notice model.Notice

	// 生成邮件验证 token
	token, err := GenerateEmailToken(service.UserID, service.OperationType, service.Email, service.Password)
	if err != nil {
	}

	//从数据库中查询与 OperationType+1 相关联的 Notice 记录
	if err := model.DB.First(&notice, service.OperationType+1).Error; err != nil {
	}

	// 从环境变量 VAILD_EMAIL 中获取基础验证链接地址，与生成的 token 拼接成完整的验证链接
	// 验证链接地址的意义在于，当用户点击邮件中的链接（如 http://localhost:8080/#/vaild/email/?token=<generated_token>）时，浏览器将导航到应用中的邮箱验证页面，并携带 token 参数。
	// 前端应用会提取 token，并通过 AJAX 或 Fetch API 向服务器发送验证请求。服务器端接收到请求后，验证 token 的有效性，如果通过验证，则完成相应的邮箱绑定、解绑或密码更改操作。
	address = os.Getenv("VAILD_EMAIL") + token
	mailStr := notice.Text
	// 将文本内容 mailStr 中的占位符 VaildAddress 替换为实际的验证链接地址 address
	mailText := strings.Replace(mailStr, "VaildAddress", address, -1)
	// 创建邮件消息实例
	m := mail.NewMessage()
	m.SetHeader("From", os.Getenv("SMTP_EMAIL")) // 发件人
	m.SetHeader("To", service.Email)             // 收件人
	//m.SetAddressHeader("Cc", "dan@example.com", "Dan")抄送
	m.SetHeader("Subject", "CMall")  // 主题
	m.SetBody("text/html", mailText) // 内容

	// host：SMTP 服务器的主机名或 IP 地址（如：QQ邮箱的host：smtp.qq.com）
	// port：SMTP 服务器端口 (如：qq邮箱的smtp开启端口为465)
	// username：SMTP 服务器要求的身份验证用户名
	// password: 与 username 对应的密码或授权码。
	d := mail.NewDialer(os.Getenv("SMTP_HOST"), 465, os.Getenv("SMTP_EMAIL"), os.Getenv("SMTP_PASS"))
	// 必须启用 TLS 加密
	d.StartTLSPolicy = mail.MandatoryStartTLS

	// Send the email
	if err := d.DialAndSend(m); err != nil {
	}
}
