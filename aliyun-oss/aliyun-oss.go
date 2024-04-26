package oss

import (
	"mime"
	"os"
	"path/filepath"

	"github.com/aliyun/aliyun-oss-go-sdk/oss"
	"github.com/google/uuid"
)

// UploadAvatarService 获得上传oss token的服务
type UploadAvatarService struct {
	Filename string `form:"filename" json:"filename"`
}

// Post 创建token
func (service *UploadAvatarService) Post() {
	// os.Getenv() 从环境变量中获取指定键对应的值，通过这种方式，敏感的账户凭据（Access Key ID 和 Secret）不会硬编码在代码中，而是存储在环境变量中，提高了安全性。
	// oss.New()函数的第一个参数endpoint就是 你的仓库所在的阿里云对象存储地域节点，如："oss-cn-shenzhen.aliyuncs.com"
	// 创建oss对象
	client, err := oss.New(os.Getenv("OSS_END_POINT"), os.Getenv("OSS_ACCESS_KEY_ID"), os.Getenv("OSS_ACCESS_KEY_SECRET"))
	if err != nil {
		// 填入对应逻辑
	}

	// 获取存储空间
	bucket, err := client.Bucket(os.Getenv("OSS_BUCKET"))
	if err != nil {
		// 填入对应逻辑
	}

	// 获取文件扩展名
	ext := filepath.Ext(service.Filename)

	// 用于传递给后续的 OSS API 调用作为可选参数
	options := []oss.Option{
		// oss.ContentType函数 设置 Content-Type 标头
		// mime.TypeByExtension函数 mime 是 net/http 包的子包，根据文件扩展名推断出相应的 MIME 类型。
		// 例如 .jpg 扩展名对应的 MIME 类型通常是 image/jpeg。设置正确的 Content-Type 对于浏览器正确解析和展示图片至关重要
		oss.ContentType(mime.TypeByExtension(ext)),
	}

	// 生成一个唯一的对象键（Key），用于在 OSS 存储桶中存储用户头像
	// upload/avatar/: 固定的前缀，表明这个对象存储在 upload/avatar/ 目录下，方便管理和检索。
	// uuid.Must(uuid.NewRandom()).String()：生成一个随机的 UUID（通用唯一标识符），确保对象键全局唯一。
	// Must 函数用于处理潜在的错误，如果生成 UUID 失败，会触发 panic
	// ext: 用户上传头像文件的扩展名，保持原始文件格式，便于客户端识别和处理
	key := "upload/avatar/" + uuid.Must(uuid.NewRandom()).String() + ext

	// SignURL 方法，生成一个带有签名的上传（HTTP PUT）URL。
	// key: 之前生成的唯一对象键，表示头像在 OSS 存储桶bucket中的存储位置。
	// oss.HTTPPut: 表示生成的 URL 应用于 HTTP PUT 请求，即上传操作。
	// 600: 有效期（以秒为单位），生成的签名 URL 在此期间内有效。此处设置为 600 秒（10 分钟），意味着用户必须在 10 分钟内完成头像上传。
	// options...: 传递之前定义的 options 切片，包含设置 Content-Type 的选项。这样，在使用签名 URL 上传头像时，OSS 会自动应用正确的 Content-Type。
	signedPutURL, err := bucket.SignURL(key, oss.HTTPPut, 600, options...)
	if err != nil {
		// 填入对应逻辑
	}
	// 查看图片
	// 生成一个带有签名的下载（HTTP GET）URL
	signedGetURL, err := bucket.SignURL(key, oss.HTTPGet, 600)
	if err != nil {
		// 填入对应逻辑
	}

	return // 返回对应逻辑
}
