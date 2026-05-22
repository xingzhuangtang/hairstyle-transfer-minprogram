# 用户模式实现报告

## 用户需求

### 三种用户模式定义

| 模式 | 条件 | 说明 |
|------|------|------|
| **游客模式** | 未绑定微信且未绑定手机号 | 首次进入自动获取 openid，赠送 198 根梳子发丝 |
| **普通用户模式** | 已绑定微信 (openid) 或 手机号 | 注册完成，有完整的用户账户 |
| **会员模式** | 普通用户 + VIP 会员资格 | 购买了 VIP 会员，享受 50% 折扣 |

### 模式流转逻辑

```
首次进入 → 游客模式 (openid)
         ↓ 绑定微信/手机号
      普通用户模式
         ↓ 购买 VIP
      会员模式
```

### 下次进入逻辑

- **游客**：下次进入仍是游客（除非绑定了微信/手机）
- **普通用户**：下次进入自动以普通用户身份登录
- **会员**：下次进入自动以会员身份登录

## 实现方案

### 1. 后端数据库设计 (`models.py`)

```python
class User(db.Model):
    # 用户类型
    user_type = db.Column(db.Enum('guest', 'registered', 'member'), 
                          default='registered', 
                          comment='用户类型：guest=游客，registered=已注册，member=会员')
    
    # 会员等级
    member_level = db.Column(db.Enum('normal', 'vip'), 
                             default='normal', 
                             comment='会员等级')
```

### 2. 后端登录逻辑 (`auth.py`)

微信登录接口根据 `user_type` 和 `member_level` 自动判断用户模式：

```python
def wechat_login(self, code):
    # 获取 openid
    # ...
    
    # 查询或创建用户
    user = User.query.filter_by(openid=openid).first()
    
    if not user:
        # 首次登录，创建游客账户
        user = User(
            openid=openid,
            user_type='guest',
            member_level="normal",
        )
        # 授予游客首次赠送（198 根梳子发丝）
        # ...
    else:
        # 老用户，根据类型判断模式
        # 游客模式：user_type='guest'
        # 普通用户模式：user_type='registered' 且 member_level='normal'
        # 会员模式：user_type='registered' 且 member_level='vip'
    
    return {
        "success": True,
        "user_type": user.user_type,
        "member_level": user.member_level,
        "user": user.to_dict(),
    }
```

### 3. 前端自动登录 (`app.js`)

在 `onLaunch` 时自动执行游客登录：

```javascript
onLaunch() {
  console.log('小程序启动')
  // 自动游客登录（获取 openid）
  this.initGuestMode()
}

async initGuestMode() {
  const res = await guestLogin()
  
  if (res.success) {
    const userInfo = res.user
    this.globalData.token = res.token
    this.globalData.userInfo = userInfo
    this.globalData.isPremium = userInfo.member_level === 'vip'
    
    console.log('自动登录成功:', {
      user_type: userInfo.user_type,
      member_level: userInfo.member_level,
      nickname: userInfo.nickname
    })
  }
}
```

### 4. 前端用户模式判断 (`utils/auth.js`)

```javascript
/**
 * 判断用户模式
 * @param {Object} user - 用户信息
 * @returns {string} - 'guest' | 'normal' | 'vip'
 */
export function getUserMode(user) {
  if (!user) return 'guest'

  // 游客模式：user_type='guest'
  if (user.user_type === 'guest') {
    return 'guest'
  }

  // 会员模式：member_level='vip'
  if (user.member_level === 'vip') {
    return 'vip'
  }

  // 普通用户模式
  return 'normal'
}
```

### 5. 游客绑定手机/微信后升级 (`auth.py`)

```python
def phone_login(self, phone, code):
    # 1. 先按手机号查找
    user = User.query.filter_by(phone=phone).first()
    
    if not user:
        # 检查当前请求是否有 openid 用户（游客）
        token = request.headers.get("Authorization")
        # 解码 token 获取当前用户
        
        # 如果有 openid 用户且未绑定手机号，直接绑定
        if current_user and current_user.openid and not current_user.phone:
            user = current_user
            user.phone = phone
            # 游客绑定手机号后，更新用户类型为 registered
            if user.user_type == 'guest':
                user.user_type = 'registered'
            db.session.commit()
```

## 用户体验流程

### 首次使用（游客模式）

1. 用户打开小程序
2. 自动执行 `guestLogin()`，获取 openid
3. 后端创建游客账户 (`user_type='guest'`)
4. 赠送 198 根梳子发丝
5. 显示提示："新用户注册成功！198 根梳子发丝已到账"

### 绑定手机/微信（升级为普通用户）

1. 游客点击"去注册"或"绑定手机"
2. 输入手机号和验证码
3. 后端将 `user_type` 从 `guest` 更新为 `registered`
4. 赠送 1000 根梳子发丝（注册福利）
5. 下次进入自动以普通用户身份登录

### 购买 VIP（升级为会员）

1. 普通用户点击"购买会员"
2. 支付 99 元
3. 后端设置 `member_level='vip'`
4. 赠送 1000 根梳子发丝（会员福利）
5. 下次进入自动以会员身份登录

## 修改的文件列表

| 文件 | 修改内容 |
|------|---------|
| `backend/auth.py` | 更新 `wechat_login` 返回 `user_type` 和 `member_level` |
| `backend/auth.py` | 更新 `phone_login` 和 `bind_phone` 处理游客升级 |
| `backend/models.py` | 已有 `user_type` 和 `member_level` 字段 |
| `miniprogram/app.js` | 添加 `initGuestMode()` 在 `onLaunch` 自动登录 |
| `miniprogram/app.js` | 添加 `getUserMode()` 判断用户模式 |
| `miniprogram/utils/auth.js` | 更新 `guestLogin()` 处理三种模式 |
| `miniprogram/utils/auth.js` | 新增 `getUserMode()` 函数 |
| `miniprogram/pages/index/index.js` | 移除重复的 `initGuestMode()` |

## 开发者模式隔离

同时，为了确保开发者模式不影响用户模式验证，实现了环境变量控制方案：

- **主开关**: `DEVELOPER_MODE_ENABLED` (默认 `false`)
- **账号列表**: `DEVELOPER_ACCOUNTS` (默认空)

只有同时满足两个条件，开发者模式才启用。详见 `DEVELOPER_MODE_FIX.md`。

## 完成日期

2026-04-17
