# 实时聊天系统设计文档

> 发型迁移小程序 — 用户与管理员双向聊天系统
> 日期: 2025-06-05
> 方案: A（消息轮询模式）

---

## 1. 数据库设计

### 1.1 `chat_messages` 表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | BIGINT | PK, AUTO_INCREMENT | 主键 |
| `user_id` | BIGINT | NOT NULL, FK→users.id | 发送者用户ID（用户消息=用户ID，管理员回复=0） |
| `sender_type` | ENUM('user', 'admin') | NOT NULL | 发送者类型 |
| `content` | TEXT | NOT NULL | 消息内容（最长2000字符） |
| `is_read` | TINYINT(1) | DEFAULT 0 | 是否已读（0=未读，1=已读） |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 1.2 SQL DDL

```sql
CREATE TABLE chat_messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL COMMENT '关联用户ID（管理员消息时为0）',
    sender_type ENUM('user', 'admin') NOT NULL COMMENT '发送者类型',
    content TEXT NOT NULL COMMENT '消息内容',
    is_read TINYINT(1) DEFAULT 0 COMMENT '是否已读：0=未读，1=已读',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id_created (user_id, created_at DESC),
    INDEX idx_user_id_unread (user_id, sender_type, is_read),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表';
```

### 1.3 索引设计说明

- **`idx_user_id_created`**: 复合索引，支持按用户查询聊天历史并按时间排序（轮询接口的核心查询）
- **`idx_user_id_unread`**: 复合索引，支持快速统计某用户收到的未读管理员消息数
- `user_id` 使用外键约束（`ON DELETE CASCADE`），用户删除时自动清理聊天记录

### 1.4 迁移脚本 `migrate_chat_messages.py`

遵循项目现有迁移脚本模式（参考 `migrate_messages_table.py`）：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：创建 chat_messages 表
用于实时聊天功能
"""

import os
import sys
from flask import Flask
from config import get_config

def migrate():
    config = get_config()
    db_url = (
        f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}"
        f"@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE}"
        f"?charset=utf8mb4"
    )
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True

    from models import db, ChatMessage
    db.init_app(app)

    with app.app_context():
        db.create_all()
        print("✅ chat_messages 表创建成功")

        # 验证表结构
        import pymysql
        connection = pymysql.connect(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("DESCRIBE chat_messages")
                columns = cursor.fetchall()
                print("\n📋 chat_messages 表结构:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]}")
        finally:
            connection.close()

if __name__ == '__main__':
    try:
        migrate()
        print("\n🎉 迁移完成！")
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

---

## 2. 后端 API 设计

### 2.1 `POST /api/chat/send` — 用户发送消息

**认证**: JWT Bearer Token（`login_required`）

**请求体**:
```json
{
  "content": "我想咨询一下发型迁移的效果"
}
```

**响应** (200):
```json
{
  "success": true,
  "message": {
    "id": 1,
    "sender_type": "user",
    "content": "我想咨询一下发型迁移的效果",
    "is_read": false,
    "created_at": "2025-06-05T10:30:00"
  }
}
```

**错误响应**:
- 400: 内容为空 / 超过2000字符
- 401: 未登录
- 403: 账号已注销
- 429: 发送频率过高（限流）

**业务逻辑**:
1. 验证 content 非空且 <= 2000 字符
2. 清理 HTML 标签（防 XSS）
3. 插入 `chat_messages` 表，`sender_type='user'`, `is_read=0`
4. 调用 `ChatNotifier` 发送企业微信通知给管理员（异步，不阻塞响应）
5. 返回创建的消息对象

### 2.2 `GET /api/chat/messages` — 轮询获取消息

**认证**: JWT Bearer Token（`login_required`）

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `since` | ISO 8601 时间戳 | 否 | 获取此时间之后的新消息，不传则返回最近50条 |

**请求示例**: `GET /api/chat/messages?since=2025-06-05T10:30:00`

**响应** (200):
```json
{
  "success": true,
  "messages": [
    {
      "id": 5,
      "sender_type": "admin",
      "content": "您好，请问有什么可以帮您？",
      "is_read": true,
      "created_at": "2025-06-05T10:31:00"
    }
  ],
  "has_more": false,
  "server_time": "2025-06-05T10:32:00"
}
```

**业务逻辑**:
1. 如果 `since` 为空，返回最近 50 条消息（按 `created_at DESC`）
2. 如果 `since` 有值，返回 `created_at > since` 的所有消息（最多200条防溢出）
3. 将返回的管理员消息（`sender_type='admin'`）标记为已读（`is_read=1`）
4. `server_time` 用于前端时钟同步校准

### 2.3 `POST /api/chat/reply` — 管理员回复

**认证**: HMAC-SHA256 签名 Token（URL 参数，参考 `refund_notifier.py` 模式）

**请求参数**（query string）:
| 参数 | 类型 | 说明 |
|------|------|------|
| `token` | string | HMAC 签名 token（包含 user_id 和时间戳） |
| `action` | string | 固定为 `reply` |

**请求体**:
```json
{
  "content": "您好，发型迁移支持素描效果，您可以在结果页面选择开启。"
}
```

**响应** (200):
```json
{
  "success": true,
  "message": "回复已发送"
}
```

**错误响应**:
- 400: token 无效/过期/内容不合法
- 404: 目标用户不存在

**Token 设计**:
- 使用与 `refund_service.py` 相同的 `HMAC-SHA256` 方案
- Payload: `{user_id}:{timestamp}:{signature}`
- 有效期: 24 小时（86400 秒）
- 使用 `JWT_SECRET_KEY` 作为 HMAC 密钥

### 2.4 `GET /api/chat/unread-count` — 获取未读消息数

**认证**: JWT Bearer Token（`login_required`）

**响应** (200):
```json
{
  "success": true,
  "unread_count": 3
}
```

**业务逻辑**:
- 查询 `chat_messages WHERE user_id = ? AND sender_type = 'admin' AND is_read = 0`
- 返回 COUNT

### 2.5 速率限制

在 `/api/chat/send` 接口实现简单内存限流（无需 Redis）：

```python
# 简单内存限流（按 user_id）
_send_timestamps = {}  # {user_id: [timestamp, ...]}
_SEND_LIMIT = 5        # 每分钟最多5条
_SEND_WINDOW = 60      # 60秒窗口
```

---

## 3. 企业微信集成

### 3.1 `ChatNotifier` 类

复用 `refund_notifier.py` 的 `_get_access_token()` 模式：

```python
class ChatNotifier:
    """企业微信聊天通知"""

    def __init__(self):
        self.config = get_config()
        self.wechat_corp_id = self.config.WECHAT_CORP_ID
        self.wechat_corp_secret = self.config.WECHAT_CORP_SECRET
        self.wechat_agent_id = self.config.WECHAT_AGENT_ID
        self.base_url = os.getenv("SERVER_URL", "https://xn--gmq63iba0780e.com")

    def send_new_message_notification(self, user, message):
        """发送新消息通知到企业微信"""
        try:
            access_token = self._get_access_token()

            # 生成回复链接 token
            from chat_service import ChatService
            reply_token = ChatService.generate_reply_token(user.id)

            reply_url = f"{self.base_url}/api/chat/reply?token={reply_token}&action=reply"

            # template_card 消息
            message_content = {
                "touser": "@all",
                "msgtype": "template_card",
                "agentid": int(self.wechat_agent_id),
                "template_card": {
                    "card_type": "text_notice",
                    "main_title": {
                        "title": "新聊天消息",
                        "desc": f"{user.nickname or '用户'}({user.id}) 发来消息"
                    },
                    "sub_title_text": f"消息内容: {message.content[:100]}",
                    "jump_list": [
                        {
                            "type": 1,
                            "url": reply_url,
                            "title": "立即回复"
                        }
                    ],
                    "card_action": {
                        "type": 1,
                        "url": reply_url
                    }
                }
            }

            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            response = requests.post(send_url, json=message_content, timeout=10)

            if response.status_code != 200:
                print(f"❌ 企业微信消息发送失败: HTTP {response.status_code}")
                return False

            result = response.json()
            if result.get("errcode", -1) == 0:
                print(f"✅ 聊天消息通知已发送到企业微信")
                return True
            else:
                print(f"❌ 企业微信返回错误: {result}")
                return False

        except Exception as e:
            print(f"❌ 发送企业微信通知异常: {e}")
            return False

    def _get_access_token(self):
        """获取企业微信 access_token（与 refund_notifier 相同模式）"""
        if not self.wechat_corp_id or not self.wechat_corp_secret:
            raise Exception("企业微信配置不完整")

        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.wechat_corp_id}&corpsecret={self.wechat_corp_secret}"
        response = requests.get(token_url, timeout=10)

        if response.status_code != 200:
            raise Exception(f"获取 access_token 失败: HTTP {response.status_code}")

        token_data = response.json()
        if token_data.get("errcode", 0) != 0:
            raise Exception(f"获取 access_token 失败: {token_data}")

        return token_data["access_token"]
```

### 3.2 Token 安全

在 `chat_service.py` 中实现，复用 `refund_service.py` 的 HMAC 模式：

```python
class ChatService:
    @staticmethod
    def generate_reply_token(user_id):
        """生成 HMAC-SHA256 签名的回复 token"""
        config = get_config()
        secret_key = config.JWT_SECRET_KEY
        timestamp = str(int(time.time()))
        message = f"{user_id}:{timestamp}"

        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        raw = f"{user_id}:{timestamp}:{signature}"
        return base64.urlsafe_b64encode(raw.encode()).decode()

    @staticmethod
    def verify_reply_token(token, max_age=86400):
        """验证回复 token"""
        try:
            config = get_config()
            secret_key = config.JWT_SECRET_KEY

            raw = base64.urlsafe_b64decode(token.encode()).decode()
            parts = raw.split(':')
            if len(parts) != 3:
                return None, 'Invalid token format'

            user_id, timestamp, signature = parts

            if int(time.time()) - int(timestamp) > max_age:
                return None, 'Token expired'

            message = f"{user_id}:{timestamp}"
            expected = hmac.new(
                secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            if signature != expected:
                return None, 'Invalid signature'

            return int(user_id), None
        except Exception as e:
            return None, f'Token decode failed: {str(e)}'
```

---

## 4. 前端设计

### 4.1 文件结构

```
miniprogram/pages/chat/
├── chat.js        # 页面逻辑
├── chat.wxml      # 页面模板
├── chat.wxss      # 页面样式
└── chat.json      # 页面配置
```

### 4.2 聊天页面布局

```
┌─────────────────────────────────┐
│  ← 返回    在线客服          ··· │  ← 导航栏
├─────────────────────────────────┤
│                                 │
│  ┌──────────────────────────┐   │
│  │ 你好，请问有什么可以帮您？│   │  ← 管理员消息（左侧）
│  │        10:30             │   │
│  └──────────────────────────┘   │
│                                 │
│         ┌──────────────────┐    │
│         │我想咨询发型迁移   │    │  ← 用户消息（右侧）
│         │        10:31     │    │
│         └──────────────────┘    │
│                                 │
├─────────────────────────────────┤
│  ┌──────────────┐  ┌─────────┐ │
│  │ 输入消息...   │  │  发送   │ │  ← 底部输入区
│  └──────────────┘  └─────────┘ │
└─────────────────────────────────┘
```

### 4.3 核心功能

#### 4.3.1 消息数据结构

```javascript
// 消息对象
{
  id: 1,
  sender_type: 'user' | 'admin',
  content: '消息内容',
  is_read: true,
  created_at: '2025-06-05T10:30:00',
  status: 'sending' | 'sent' | 'failed'  // 仅前端使用
}
```

#### 4.3.2 轮询机制

```javascript
// chat.js 核心轮询逻辑
Page({
  data: {
    messages: [],
    inputContent: '',
    sending: false,
    polling: false,
    lastPollTime: null,
    connectionStatus: 'connected'  // connected | disconnected | reconnecting
  },

  // 5秒轮询
  POLL_INTERVAL: 5000,
  MAX_RETRY_COUNT: 3,
  RETRY_DELAY: 2000,

  onShow() {
    this.loadChatHistory()
    this.startPolling()
    this.updateUnreadBadge()
  },

  onHide() {
    this.stopPolling()
  },

  onUnload() {
    this.stopPolling()
  },

  startPolling() {
    if (this.data.polling) return
    this.setData({ polling: true })

    this.pollTimer = setInterval(() => {
      this.pollNewMessages()
    }, this.POLL_INTERVAL)
  },

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
    this.setData({ polling: false })
  },

  async pollNewMessages() {
    try {
      const since = this.data.lastPollTime
      const res = await get('/api/chat/messages', since ? { since } : {})

      if (res.success && res.messages && res.messages.length > 0) {
        this.setData({
          messages: [...this.data.messages, ...res.messages],
          lastPollTime: res.server_time
        })
        // 有新消息时自动滚动到底部
        this.scrollToBottom()
      } else {
        // 即使无新消息也更新 server_time
        if (res.server_time) {
          this.setData({ lastPollTime: res.server_time })
        }
      }
      this.setData({ connectionStatus: 'connected' })
    } catch (err) {
      console.error('轮询失败:', err)
      this.setData({ connectionStatus: 'disconnected' })
    }
  },

  scrollToBottom() {
    // 使用 scroll-view 的 scroll-into-view 属性
    const lastMsg = this.data.messages[this.data.messages.length - 1]
    if (lastMsg) {
      this.setData({ scrollToView: `msg-${lastMsg.id}` })
    }
  }
})
```

#### 4.3.3 发送消息

```javascript
async onSendMessage() {
  const content = this.data.inputContent.trim()
  if (!content || this.data.sending) return

  // 乐观更新：先显示发送中状态
  const tempMsg = {
    id: Date.now(),
    sender_type: 'user',
    content: content,
    is_read: true,
    created_at: new Date().toISOString(),
    status: 'sending'
  }

  this.setData({
    messages: [...this.data.messages, tempMsg],
    inputContent: '',
    sending: true
  })
  this.scrollToBottom()

  try {
    const res = await post('/api/chat/send', { content })
    if (res.success) {
      // 更新消息状态为已发送
      const msgs = this.data.messages.map(m =>
        m.id === tempMsg.id ? { ...res.message, status: 'sent' } : m
      )
      this.setData({ messages: msgs })
    }
  } catch (err) {
    // 标记为发送失败
    const msgs = this.data.messages.map(m =>
      m.id === tempMsg.id ? { ...m, status: 'failed' } : m
    )
    this.setData({ messages: msgs })
    wx.showToast({ title: '发送失败，请重试', icon: 'none' })
  } finally {
    this.setData({ sending: false })
  }
}
```

#### 4.3.4 未读角标

在 `app.js` 的 `onLaunch` 和 `onShow` 中，通过 `TabBar` 入口展示未读角标：

```javascript
// 进入小程序时检查未读
async checkUnreadCount() {
  try {
    const res = await get('/api/chat/unread-count')
    if (res.success && res.unread_count > 0) {
      wx.setTabBarBadge({
        index: 1,  // "我的" tab 的索引
        text: String(res.unread_count > 99 ? '99+' : res.unread_count)
      })
    } else {
      wx.removeTabBarBadge({ index: 1 })
    }
  } catch (err) {
    // 静默失败
  }
}
```

### 4.4 新增 API 封装 `miniprogram/api/chat.js`

```javascript
import { get, post } from '../utils/request.js'

// 发送消息
export function sendChatMessage(content) {
  return post('/api/chat/send', { content })
}

// 获取消息（轮询）
export function getChatMessages(since) {
  const params = since ? { since } : {}
  return get('/api/chat/messages', params)
}

// 获取未读数
export function getUnreadCount() {
  return get('/api/chat/unread-count')
}
```

---

## 5. 文件变更清单

### 5.1 新建文件

| 文件 | 说明 |
|------|------|
| `backend/models.py` (新增 ChatMessage 类) | 聊天消息数据模型 |
| `backend/chat_service.py` | 聊天业务服务（token 生成/验证、限流逻辑） |
| `backend/chat_notifier.py` | 企业微信聊天通知器 |
| `backend/migrate_chat_messages.py` | 数据库迁移脚本 |
| `miniprogram/pages/chat/chat.js` | 聊天页面逻辑 |
| `miniprogram/pages/chat/chat.wxml` | 聊天页面模板 |
| `miniprogram/pages/chat/chat.wxss` | 聊天页面样式 |
| `miniprogram/pages/chat/chat.json` | 聊天页面配置 |
| `miniprogram/api/chat.js` | 聊天 API 封装 |
| `backend/templates/chat_reply.html` | 管理员回复页面（H5） |

### 5.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `backend/models.py` | 新增 `ChatMessage` 模型类 |
| `backend/api.py` | 新增 4 个聊天 API 路由 + 回复页面路由 |
| `miniprogram/app.json` | 注册 `pages/chat/chat` 页面 |
| `miniprogram/app.js` | 新增全局未读消息检查逻辑 |
| `miniprogram/pages/profile/profile.js` | 新增 `goToChat()` 导航方法 |
| `miniprogram/pages/profile/profile.wxml` | 新增"在线客服"菜单入口 |
| `miniprogram/pages/profile/profile.wxss` | 如有需要，新增角标样式 |

### 5.3 不需要修改的文件

- `backend/app.py` — 不需要修改，蓝图注册在 `api.py` 中完成
- `backend/config.py` — 不需要修改，复用现有企业微信配置
- `backend/refund_notifier.py` — 不变，作为模式参考
- `backend/refund_service.py` — 不变，token 模式参考

---

## 6. 安全考虑

### 6.1 速率限制

- 每个用户每分钟最多发送 5 条消息
- 使用内存字典 `{user_id: [timestamps]}` 实现滑动窗口限流
- 超过限制返回 429 状态码

```python
_send_timestamps = {}

def check_rate_limit(user_id):
    now = time.time()
    if user_id not in _send_timestamps:
        _send_timestamps[user_id] = []

    # 清理过期时间戳
    _send_timestamps[user_id] = [
        ts for ts in _send_timestamps[user_id]
        if now - ts < 60
    ]

    if len(_send_timestamps[user_id]) >= 5:
        return False

    _send_timestamps[user_id].append(now)
    return True
```

### 6.2 输入清洗

- 后端: 使用 `re.sub(r'<[^>]+>', '', content)` 移除 HTML 标签
- 后端: 使用 `content.strip()` 去除首尾空白
- 后端: 限制最大长度 2000 字符
- 前端: `<textarea maxlength="2000">` 原生限制
- 前端: 发送前 `trim()` 处理

### 6.3 Token 安全

- 管理员回复 token 使用 HMAC-SHA256 签名
- 24 小时过期
- Token 绑定到特定 `user_id`，不能跨用户回复
- 使用项目现有的 `JWT_SECRET_KEY`，无需新增密钥

### 6.4 XSS 防护

- 后端存储前移除 HTML 标签
- 前端使用 `<text>` 渲染消息内容（小程序自动转义）
- 管理员回复页面（H5）使用 `textContent` 而非 `innerHTML`

### 6.5 SQL 注入防护

- 使用 SQLAlchemy ORM 插入和查询
- 所有参数通过 ORM 绑定，不使用原始 SQL

---

## 7. 边界情况处理

### 7.1 用户注销账号

- `login_required` 装饰器已检查 `user.is_deactivated`，注销用户无法发送消息
- 用户注销后，`ON DELETE CASCADE` 自动删除其聊天记录
- 管理员回复已注销用户的消息时，返回 404

### 7.2 消息过长

- 前端: `<textarea maxlength="2000">` 原生限制
- 后端: `if len(content) > 2000: return 400`
- 数据库: `TEXT` 类型支持 ~65KB，2000字符绰绰有余

### 7.3 网络断开时的轮询

- 前端维护 `connectionStatus` 状态
- 连续 3 次失败后停止轮询，显示"网络断开"提示
- 提供手动刷新按钮
- 网络恢复后（`onShow`）自动重新开始轮询
- 轮询失败不阻塞 UI，历史消息仍然可见

### 7.4 管理员长时间不回复

- 不实现自动回复（避免误导用户）
- 前端在消息列表中显示提示："管理员将在工作时间尽快回复"
- 用户发送消息后，如果 5 分钟内无管理员回复，显示友好提示

### 7.5 多用户并发聊天

- 每条消息都有 `user_id` 隔离，不同用户的聊天完全独立
- 管理员通过企业微信通知中的 `user_id` 知道回复对象
- 轮询只返回当前登录用户的消息，不会泄露其他用户数据

### 7.6 消息乱序

- 数据库按 `created_at` 排序返回
- 前端轮询按 `since` 时间戳获取增量消息
- 前端维护 `server_time` 确保时间同步
- 消息 ID 自增保证全局有序

### 7.7 企业微信通知失败

- 通知失败不影响消息入库（try/except 包裹）
- 通知失败打印日志，不影响用户体验
- 管理员仍可通过其他方式（如直接查询数据库）发现消息

---

## 8. 实现顺序

### Phase 1: 数据库 + 模型 (30分钟)
1. 在 `models.py` 中添加 `ChatMessage` 模型
2. 编写 `migrate_chat_messages.py` 迁移脚本
3. 执行迁移，验证表结构

### Phase 2: 后端 API (1小时)
1. 创建 `chat_service.py`（token 生成/验证、限流）
2. 创建 `chat_notifier.py`（企业微信通知）
3. 在 `api.py` 中新增 4 个路由 + 管理员回复页面
4. 创建 `chat_reply.html` 管理员回复页面模板

### Phase 3: 前端页面 (1.5小时)
1. 创建 `miniprogram/api/chat.js` API 封装
2. 创建 `miniprogram/pages/chat/` 四个文件
3. 修改 `app.json` 注册页面
4. 修改 `profile.js/wxml` 添加入口

### Phase 4: 集成测试 (30分钟)
1. 测试用户发送消息
2. 测试企业微信通知
3. 测试管理员回复
4. 测试轮询获取消息
5. 测试未读计数
6. 测试边界情况

---

## 9. API 路由总览

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/chat/send` | JWT | 用户发送消息 |
| GET | `/api/chat/messages` | JWT | 轮询获取消息 |
| GET | `/api/chat/unread-count` | JWT | 获取未读数 |
| POST | `/api/chat/reply` | HMAC Token | 管理员回复 |
| GET | `/api/chat/reply` | HMAC Token | 管理员回复页面（H5） |

---

## 10. 管理员回复页面 (H5)

管理员通过企业微信通知中的链接打开浏览器 H5 页面进行回复。

页面功能：
1. 显示该用户的昵称、ID
2. 显示该用户最近的聊天历史（最近20条）
3. 文本输入框 + 发送按钮
4. 发送成功后刷新聊天历史

页面通过 URL token 识别目标用户：
```
https://xn--gmq63iba0780e.com/api/chat/reply?token=<HMAC_TOKEN>&action=reply
```

页面验证 token 后，渲染 Flask 模板（非 SPA），直接 POST 表单提交回复。

---

## 11. 与企业微信通知的交互流程

```
用户发送消息
    ↓
POST /api/chat/send (JWT认证)
    ↓
存入 chat_messages (sender_type='user', is_read=0)
    ↓
ChatNotifier.send_new_message_notification()
    ↓
企业微信收到 template_card 通知
    ↓
管理员点击"立即回复"按钮
    ↓
浏览器打开 /api/chat/reply?token=xxx&action=reply
    ↓
验证 token → 显示用户信息和聊天历史
    ↓
管理员输入回复内容 → 提交
    ↓
POST /api/chat/reply (token认证)
    ↓
存入 chat_messages (sender_type='admin', is_read=0)
    ↓
前端轮询检测到新消息 → 显示在聊天界面
```

