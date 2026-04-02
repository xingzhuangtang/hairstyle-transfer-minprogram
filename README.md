# 发型迁移微信小程序 💇‍♂️

基于 AI 技术的微信小程序发型迁移应用，支持发型虚拟试戴、素描风格转换等功能。

[![Security Audit](https://img.shields.io/badge/security-audited-green)](docs/SECURITY_AUDIT.md)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![WeChat](https://img.shields.io/badge/platform-WeChat-07c160)](https://developers.weixin.qq.com/miniprogram/dev/framework/)

---

## ✨ 功能特性

### 核心功能

- 🎨 **发型提取** - 从照片中提取发型轮廓
- 💫 **发型迁移** - 将发型虚拟试戴到目标照片
- 🎭 **素描转换** - AI 生成素描风格效果
- 💰 **虚拟货币** - 发丝系统（剪刀卡槽/梳子卡槽）
- 👑 **会员系统** - VIP 会员享 50% 折扣
- 📱 **微信支付** - 在线充值和会员购买

### 商业化功能

- ✅ 新用户注册赠送 1000 发丝
- ✅ 余额不足自动赠送（4 小时触发）
- ✅ VIP 会员历史记录保存 45 天
- ✅ 会员到期自动降级和提醒
- ✅ 完整的用户协议和隐私政策

---

## 🏗 技术架构

```
┌─────────────────┐         ┌─────────────────┐
│   微信小程序     │  HTTPS  │  Flask 后端      │
│  (miniprogram/) │ ←────→  │  (backend/)     │
└─────────────────┘         └────────┬────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
         ▼                            ▼                            ▼
   ┌───────────┐              ┌───────────┐              ┌───────────┐
   │   MySQL   │              │   Redis   │              │阿里云 API  │
   │  数据库    │              │   缓存    │              │AI 服务     │
   └───────────┘              └───────────┘              └───────────┘
```

### 技术栈

**前端 (微信小程序)**
- 微信小程序原生框架
- JavaScript / WXML / WXSS

**后端**
- Python 3.8+
- Flask Web 框架
- SQLAlchemy ORM
- Redis 缓存

**AI 服务**
- 阿里云头发分割 API
- 阿里云人脸融合 API
- 百炼素描转换 API

**支付**
- 微信支付 API v3
- 支付宝支付（可选）

---

## 📦 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+
- Redis 5.0+
- 微信小程序开发者工具

### 后端部署

1. **克隆项目**
```bash
git clone https://github.com/xingzhuangtang/hairstyle-transfer-minprogram.git
cd hairstyle-transfer-minprogram/backend
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入真实配置
```

4. **初始化数据库**
```bash
python init_db.py
```

5. **启动服务**
```bash
python app.py
# 访问 http://localhost:5003
```

### 前端部署

1. **打开微信开发者工具**
2. **导入项目** - 选择 `miniprogram/` 目录
3. **配置域名** - 在 `utils/constants.js` 中设置 API 地址
4. **编译运行**

---

## 📁 项目结构

```
hairstyle-transfer-minprogram/
├── backend/                    # Flask 后端
│   ├── app.py                 # 应用入口
│   ├── api.py                 # API 路由
│   ├── models.py              # 数据模型
│   ├── config.py              # 配置管理
│   ├── auth.py                # 认证服务
│   ├── payment_service.py     # 支付服务
│   ├── hair_service.py        # 头发服务
│   ├── member_service.py      # 会员服务
│   ├── wechat_pay.py          # 微信支付 SDK
│   ├── aliyun_hair_transfer_fixed.py  # AI 服务
│   ├── requirements.txt       # Python 依赖
│   ├── .env.example           # 环境变量模板
│   └── docs/                  # 文档
├── miniprogram/               # 微信小程序
│   ├── pages/                 # 页面
│   │   ├── index/             # 首页
│   │   ├── login/             # 登录页
│   │   ├── profile/           # 个人中心
│   │   ├── balance/           # 余额充值
│   │   ├── member/            # 会员中心
│   │   ├── history/           # 历史记录
│   │   └── legal/             # 协议页面
│   ├── utils/                 # 工具函数
│   └── app.js                 # 小程序入口
└── docs/                      # 文档
    ├── SECURITY_AUDIT.md      # 安全审查报告
    └── commercial_deployment_review.md  # 商业化部署审查
```

---

## 🔐 安全说明

### 敏感信息保护

以下文件**绝对不能**提交到 Git：

```bash
backend/.env                    # 环境变量（含 API 密钥）
backend/certs/wechat/*.pem      # 微信支付证书
backend/certs/alipay/*.pem      # 支付宝证书
backend/static/uploads/         # 用户上传文件
backend/logs/                   # 日志文件
*.db, *.sqlite                  # 数据库文件
```

### 推荐的安全实践

1. **生产环境配置**
   - 使用强密码和随机密钥
   - 启用 HTTPS
   - 限制数据库访问

2. **API 密钥管理**
   - 使用环境变量存储
   - 定期轮换密钥
   - 不提交到版本控制

详见：[安全审查报告](docs/SECURITY_AUDIT.md)

---

## 📋 配置说明

### 环境变量（.env）

```bash
# 阿里云 API 配置
ALIBABA_CLOUD_ACCESS_KEY_ID=your_key_id
ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_secret
DASHSCOPE_API_KEY=your_dashscope_key

# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=hairstyle_transfer

# 微信支付配置
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
WECHAT_MCH_ID=your_merchant_id
WECHAT_PAY_CERT_PATH=/path/to/cert.pem
WECHAT_PAY_KEY_PATH=/path/to/key.pem
WECHAT_PAY_API_V3_KEY=your_v3_key

# JWT 配置
JWT_SECRET_KEY=your_secret_key
```

完整配置参考：[backend/.env.example](backend/.env.example)

---

## 🧪 测试

```bash
# 运行测试
python test_ai_services.py
python test_payment_gateways.py
python test_virtual_currency.py
python test_performance.py
```

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📞 联系方式

- GitHub: [@xingzhuangtang](https://github.com/xingzhuangtang)
- 项目仓库：[hairstyle-transfer-minprogram](https://github.com/xingzhuangtang/hairstyle-transfer-minprogram)

---

## 📊 项目状态

- 🚧 功能继续完善中

---

*最后更新：2026-04-02*
