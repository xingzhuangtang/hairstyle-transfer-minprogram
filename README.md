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
- ✅ VIP 会员历史记录保存 45 天，过期自动删除
- ✅ 会员到期自动降级和提醒
- ✅ 完整的用户协议和隐私政策

### 客服与消息系统

- 💬 **在线客服** - 实时聊天（消息轮询），支持未读角标提醒
- 📝 **客户留言** - 留言自动通知企业微信，管理员可在企业微信内快捷回复
- 🔔 **统一未读角标** - 客服回复 + 留言处理状态合并计数
- 🔐 **HMAC 签名验证** - 企业微信回复 token 防伪造，支持过期检查

### 退款与风控

- 🛡️ **退款权限控制** - 默认隐藏"退款申请"，管理员可按用户单独授权
- 🔄 **退款自动扣回发丝** - 退款审批后自动扣除对应发丝
- 📋 **退款审批流程** - 企业微信审批 + 财务流水记录

### 推广与商业化

- 🎁 **推广返佣系统** - 用户专属推广码，成功推广存钱罐自动返现
- 🏆 **微信虚拟支付** - iOS 端虚拟商品订单创建与回调

### 自愈系统（三阶段闭环）

- 🔍 **Phase 1 感知层** — 环境监控打点（CPU/内存/磁盘/Redis/DB）、异常捕捉锁定、企业微信告警通知
- 🔧 **Phase 2 自愈层** — 5 个自动修复器（Redis/DB/内存/磁盘/慢查询）、内部审批流（低风险自动执行，中高风险需审批）
- 🧬 **Phase 3 进化层** — 防御规则引擎（title_contains/regex/source_module/frequency 模式匹配）、进化分析引擎（健康评分 0-100、趋势分析、风险预测）
- 📊 **监控面板** — 小程序端 4 Tab 监控页面（告警列表/系统健康/自动修复/进化分析）

### 账号体系（设备 ID 贯穿全生命周期）

- ✅ 设备 ID 自动生成（基于设备型号哈希，永不改变）
- ✅ 游客 → 注册用户 → VIP 会员，设备 ID 始终不变
- ✅ 微信登录需绑定手机号，支持自动账号合并
- ✅ 前端请求自动携带 X-Device-ID 请求头
- ✅ 通过设备 ID 可追溯用户完整生命周期数据

### 历史记录增强

- ✅ 成对图片展示（原图 + 素描效果）
- ✅ 过期倒计时（剩余天数/小时，4 色状态提示）
- ✅ 图片下载保存到手机相册
- ✅ 合并图片保存（原图+素描拼接）
- ✅ 手动删除历史记录（同时清理图片文件）
- ✅ 自动清理过期记录（定时任务每天凌晨执行）

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
│   ├── account_service.py     # 账户服务（发丝赠送、余额管理）
│   ├── virtual_payment_service.py  # 微信虚拟支付
│   ├── hair_service.py        # 头发服务
│   ├── member_service.py      # 会员服务
│   ├── chat_service.py        # 在线客服服务
│   ├── chat_notifier.py       # 企业微信通知
│   ├── refund_service.py      # 退款服务
│   ├── referral_service.py    # 推广返佣服务
│   ├── wechat_pay.py          # 微信支付 SDK
│   ├── aliyun_hair_transfer_fixed.py  # AI 服务
│   ├── self_healing/          # 自愈系统
│   │   ├── __init__.py        # 模块初始化（Phase 1/2/3）
│   │   ├── collector.py       # 环境监控打点
│   │   ├── probe.py           # 异常捕捉探针
│   │   ├── alert_manager.py   # 告警管理
│   │   ├── fixer.py           # 自动修复引擎（5 个修复器）
│   │   ├── approval.py        # 审批流管理
│   │   ├── defense_rule.py    # 防御规则引擎
│   │   ├── evolution.py       # 进化分析引擎
│   │   ├── wecom_bot.py       # 企业微信通知
│   │   ├── models.py          # 数据模型（告警/修复/审批/规则）
│   │   ├── api.py             # 监控 API（13+ 端点）
│   │   └── config.py          # 配置管理
│   ├── requirements.txt       # Python 依赖
│   ├── .env.example           # 环境变量模板
│   ├── deploy.sh              # 生产部署脚本
│   ├── migrate_*.py           # 数据库迁移脚本
│   ├── test_*.py              # 测试脚本
│   └── docs/                  # 文档
├── miniprogram/               # 微信小程序
│   ├── pages/                 # 页面
│   │   ├── index/             # 首页
│   │   ├── login/             # 登录页
│   │   ├── profile/           # 个人中心
│   │   ├── balance/           # 余额充值
│   │   ├── member/            # 会员中心
│   │   ├── history/           # 历史记录
│   │   ├── chat/              # 在线客服
│   │   ├── message/           # 客户留言
│   │   ├── refund/            # 退款申请
│   │   ├── referral/          # 推广中心（我的惊喜）
│   │   ├── monitor/           # 系统监控（4 Tab：告警/健康/修复/进化）
│   │   └── legal/             # 协议页面
│   ├── utils/                 # 工具函数
│   ├── api/                   # API 封装
│   └── app.js                 # 小程序入口
└── docs/                      # 文档
    ├── SECURITY_AUDIT.md      # 安全审查报告
    ├── chat-system-design.md  # 聊天系统设计文档
    └── commercial_deployment_review.md  # 商业化部署审查
```

---

## 🔐 安全说明

### 安全审查

项目已通过 **STRIDE 威胁模型分析**，覆盖支付回调、账户管理、部署脚本、自愈系统等核心模块，未发现 Critical/High 级别漏洞。

- 2026-06-10：支付回调、账户管理、部署脚本审查
- 2026-06-16：自愈系统 Phase 2+3 审查（自动修复/审批流/防御规则/进化分析），发现 2 个 Medium 级别问题（ReDoS、Mass Assignment）已制定修复方案

关键安全设计：
- 微信支付回调经签名验证后路由，订单处理函数二次验证订单存在性
- 所有财务操作（充值、赠送、退款）均写入 `financial_records` 表，完整审计追踪
- 所有免费/赠送发丝统一进入**梳子卡槽**（`comb_hairs`），与充值发丝（剪刀卡槽）分离管理

### 敏感信息保护

以下文件**绝对不能**提交到 Git：

```bash
backend/.env                    # 环境变量（含 API 密钥）
backend/certs/wechat/*.pem      # 微信支付证书
backend/certs/alipay/*.pem      # 支付宝证书
backend/private.key             # 私钥文件
backend/debug_config.py         # 开发者本地配置
backend/static/uploads/         # 用户上传文件
backend/logs/                   # 日志文件
```

### 推荐的安全实践

1. **生产环境配置**
   - 使用强密码和随机密钥
   - 启用 HTTPS
   - 限制数据库访问
   - 确保 `.env` 中企业微信配置完整

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

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379

# 微信支付配置
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
WECHAT_MCH_ID=your_merchant_id
WECHAT_PAY_CERT_PATH=/path/to/cert.pem
WECHAT_PAY_KEY_PATH=/path/to/key.pem
WECHAT_PAY_API_V3_KEY=your_v3_key

# 企业微信配置（客户留言通知）
WECHAT_CORP_ID=your_corp_id
WECHAT_CORP_SECRET=your_corp_secret
WECHAT_AGENT_ID=your_agent_id

# JWT 配置
JWT_SECRET_KEY=your_secret_key

# 开发者模式（调试用）
DEVELOPER_MODE_ENABLED=false
DEVELOPER_ACCOUNTS=1,2,3
```

完整配置参考：[backend/.env.example](backend/.env.example)

---

## 🧪 测试

```bash
cd backend

# 综合测试（功能 + 安全，推荐）
python test_comprehensive.py

# 专项测试
python test_ai_services.py
python test_payment_gateways.py
python test_virtual_currency.py
python test_performance.py
python test_refund_flow.py
python test_pricing_rules.py
python test_security.py
```

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 🙏 感谢

本项目由以下工具驱动开发：

- **Powered by QoderCLI**
- **Powered by Claude Code CLI**

---

## 📞 联系方式

- GitHub: [@xingzhuangtang](https://github.com/xingzhuangtang)
- 项目仓库：[hairstyle-transfer-minprogram](https://github.com/xingzhuangtang/hairstyle-transfer-minprogram)

### 微信联系

扫一扫添加微信，有问题随时沟通：

<img src="docs/images/wechat-contact.png" alt="微信联系方式" width="250">

---

## ☕ 请作者喝杯咖啡

如果觉得这个项目对你有帮助，欢迎打赏支持：

<img src="docs/images/wechat-tip.png" alt="微信打赏" width="250">

---

## 📊 项目状态

- ✅ 核心功能已完成（发型迁移、素描转换、支付、会员、客服、退款、推广）
- ✅ 自愈系统三阶段闭环已完成（感知 → 自愈 → 进化）
- 🚧 持续优化中

---

## 📝 更新日志

### v5.4 (2026-06-16)

**自愈系统 Phase 2+3**
- ✅ 自动修复引擎：5 个修复器（Redis/DB/内存/磁盘/慢查询），低风险自动执行，中高风险走审批
- ✅ 内部审批流：告警触发 → 创建审批 → 企微通知 → 开发者批准/拒绝 → 执行修复
- ✅ 防御规则引擎：支持 title_contains/regex/source_module/frequency 四种匹配模式，含冷却期机制
- ✅ 进化分析引擎：健康评分（0-100）、趋势分析（近 7 天 vs 前 7 天）、风险预测
- ✅ 监控面板扩展：小程序端从 2 Tab 扩展为 4 Tab（告警/健康/修复/进化）
- ✅ 新增 13 个 API 端点（修复/审批/防御规则/进化分析），均通过开发者权限校验
- ✅ 新增 3 张数据表：fix_executions、approval_records、defense_rules
- ✅ STRIDE 安全审查通过，未发现 Critical/High 级别漏洞

### v5.3 (2026-06-10)

**功能优化**
- ✅ 支付回调统一路由：支持充值和会员订单自动分发处理
- ✅ 财务记录完善：所有赠送发丝路径（注册、余额不足、游客、续赠）均记录财务流水
- ✅ 会员页到期时间：改为动态倒计时显示（剩余X天/小时）
- ✅ 历史记录页：头部固定显示"保留45天，到期自动清理"
- ✅ 合并图片修复：保持原始宽高比，不再强制压缩导致人脸变形

**运维改进**
- ✅ 部署脚本优化：修复 shell 语法问题，补充 10 个缺失文件，新增环境配置检查
- ✅ 企业微信配置：标记为生产环境必需，补充 SERVER_URL 配置项
- ✅ .gitignore 恢复：重新添加敏感文件忽略规则

**安全审查**
- ✅ STRIDE 威胁模型分析完成，未发现可利用漏洞
- ✅ 支付回调路由安全验证通过

### v5.2 (2026-06-06)

- ✅ 二维码保存功能优化
- ✅ 聊天记录系统完善
- ✅ 商业化部署审查

---

*最后更新：2026-06-16*
