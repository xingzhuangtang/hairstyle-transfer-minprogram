# 退款权限管理页面增强设计

## 1. 需求概述

在开发者账号的「退款权限」管理页面增加两个表单：
- **申请退款记录表单**：显示所有客户提交的退款申请（待处理 + 已处理）
- **成功退款表单**：显示已成功完成的退款记录

## 2. 后端 API 设计

### 2.1 新增接口：管理员查看所有退款申请

**接口：** `GET /api/admin/refund/applications`

**权限：** 仅开发者可访问（`is_developer()` 检查）

**请求参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 筛选状态：pending/approved/rejected/all，默认 all |
| phone | string | 否 | 按用户手机号模糊搜索 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20 |

**响应格式：**
```json
{
  "success": true,
  "applications": [
    {
      "id": 1,
      "user_id": 61,
      "user_phone": "15001190323",
      "user_nickname": "大唐打头阵",
      "applicant_name": "大唐",
      "applicant_phone": "15001190323",
      "refund_type": "recharge",
      "refund_amount": 50.00,
      "reason": "不想用了",
      "status": "approved",
      "approved_at": "2026-06-12T11:32:57",
      "rejection_reason": null,
      "created_at": "2026-06-12T11:06:38"
    }
  ],
  "total": 10,
  "has_more": false,
  "page": 1,
  "page_size": 20
}
```

**实现逻辑：**
1. 验证开发者权限
2. 构建查询：`RefundApplication.query`
3. 根据 status 参数筛选（all 则不筛选）
4. 根据 phone 参数关联 User 表模糊搜索
5. 按 created_at 降序排序
6. 分页返回

### 2.2 修改现有接口

无需修改现有接口，新增一个独立接口即可。

## 3. 前端页面设计

### 3.1 页面结构

```
refund-admin.wxml
├── Header（标题 + 副标题）
├── Tab 切换栏
│   ├── Tab 1: 退款权限（现有功能）
│   ├── Tab 2: 申请记录
│   └── Tab 3: 成功退款
├── Tab 1 内容：用户搜索 + 列表（现有）
├── Tab 2 内容：申请记录列表
│   ├── 状态筛选器（全部/待处理/已批准/已拒绝）
│   ├── 申请卡片列表
│   └── 加载更多
└── Tab 3 内容：成功退款列表
    ├── 退款卡片列表
    └── 加载更多
```

### 3.2 Tab 切换实现

```javascript
data: {
  currentTab: 0,  // 0: 权限管理, 1: 申请记录, 2: 成功退款
  // ... 其他数据
}

onTabChange(e) {
  const tab = e.currentTarget.dataset.tab
  this.setData({ currentTab: tab })
  
  if (tab === 1) {
    this.loadApplications('all')
  } else if (tab === 2) {
    this.loadApplications('approved')
  }
}
```

### 3.3 申请记录卡片设计

```
┌─────────────────────────────────────┐
│ 用户：大唐打头阵 (15001190323)       │
│ 申请金额：¥50.00                     │
│ 退款类型：充值退款                   │
│ 申请原因：不想用了                   │
│ 申请时间：2026-06-12 11:06           │
│ 状态：[待处理] / [已批准] / [已拒绝] │
│ 处理时间：2026-06-12 11:32           │
└─────────────────────────────────────┘
```

### 3.4 状态标签样式

| 状态 | 颜色 | 文字 |
|------|------|------|
| pending | 橙色 #fa8c16 | 待处理 |
| approved | 绿色 #52c41a | 已批准 |
| rejected | 红色 #ff4d4f | 已拒绝 |

## 4. 数据流

```
用户点击 Tab 2/3
    ↓
调用 loadApplications(status)
    ↓
请求 GET /api/admin/refund/applications?status=xxx
    ↓
后端验证开发者权限
    ↓
查询 RefundApplication 表
    ↓
返回分页数据
    ↓
前端渲染列表
```

## 5. 文件修改清单

### 后端
- `backend/api.py`：新增 `/api/admin/refund/applications` 接口

### 前端
- `miniprogram/pages/refund-admin/refund-admin.js`：
  - 增加 Tab 切换逻辑
  - 增加 `loadApplications()` 方法
  - 增加 `onTabChange()` 方法
- `miniprogram/pages/refund-admin/refund-admin.wxml`：
  - 增加 Tab 切换栏
  - 增加申请记录列表模板
  - 增加成功退款列表模板
- `miniprogram/pages/refund-admin/refund-admin.wxss`：
  - 增加 Tab 样式
  - 增加申请卡片样式
  - 增加状态标签样式

## 6. 测试要点

1. **权限测试**：非开发者账号无法访问新接口
2. **筛选测试**：按状态筛选正确
3. **搜索测试**：按手机号搜索正确
4. **分页测试**：加载更多功能正常
5. **Tab 切换**：切换流畅，数据正确加载
6. **空状态**：无数据时显示友好提示

## 7. 部署步骤

1. 部署后端代码到生产服务器
2. 重启后端服务
3. 在微信开发者工具中上传小程序前端代码
4. 提交审核并发布

## 8. 后续优化（可选）

- 申请记录详情页（查看完整信息）
- 批量审批功能
- 退款统计图表
- 导出退款记录为 Excel
