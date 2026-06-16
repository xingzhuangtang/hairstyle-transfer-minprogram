# 问题归档：客户档案功能 404 错误

**发生时间**: 2026-06-16  
**发现时间**: 2026-06-16  
**解决时间**: 2026-06-16  
**严重程度**: 高（核心功能不可用）  
**影响范围**: 开发者账号 - 客户档案功能

---

## 问题现象

开发者账号进入"客户档案"页面后，所有内容区域显示为空，控制台报错：

```
GET https://xn--gmq63iba0780e.com/api/dev/dashboard 404 (NOT FOUND)
GET https://xn--gmq63iba0780e.com/api/dev/customers 404 (NOT FOUND)
GET https://xn--gmq63iba0780e.com/api/dev/today 404 (NOT FOUND)
```

错误信息：`{error: "请求的资源不存在", code: 404}`

---

## 根本原因

**部署脚本同步不完整**

1. 本地 `backend/api.py` 包含 5 个 `/api/dev/` 路由：
   - `/dev/dashboard` - 存量大盘
   - `/dev/customers` - 客户列表
   - `/dev/customers/<id>` - 客户详情
   - `/dev/search` - 客户搜索
   - `/dev/today` - 今日动态

2. 生产服务器上的 `api.py` 缺少这些路由

3. 原因追溯：
   - 在部署自愈系统时，手动上传了 `app.py` 和 `self_healing/` 目录
   - 但没有重新同步 `api.py`
   - 导致服务器上的 `api.py` 仍是旧版本（客户档案功能开发前的版本）

---

## 解决方案

**立即修复**：
```bash
# 1. 上传最新的 api.py
sshpass -p '***' scp backend/api.py root@139.196.105.33:/opt/hairstyle-transfer-v5.3-release/backend/

# 2. 重启后端服务
sshpass -p '***' ssh root@139.196.105.33 'kill $(lsof -ti:5003); sleep 2; cd /opt/hairstyle-transfer-v5.3-release/backend && nohup python3 app.py > /tmp/backend.log 2>&1 &'

# 3. 验证路由
curl -s http://localhost:5003/api/dev/dashboard -H "Authorization: Bearer $TOKEN"
```

**验证结果**：
```json
{
  "success": true,
  "overview": {
    "total_users": 42,
    "total_hairs": 49996,
    "total_recharge": 380.0
  },
  "user_distribution": {
    "guest": 25,
    "normal": 16,
    "vip_active": 1
  }
}
```

---

## 预防措施

### 1. 部署脚本改进（已实施）

`deploy.sh` 中的 `CORE_FILES` 列表必须包含所有核心文件：

```bash
CORE_FILES=(
    "app.py"
    "api.py"              # ✅ 必须包含
    "models.py"
    "auth.py"
    "config.py"
    # ... 其他文件
)
```

### 2. 部署后验证清单

每次部署后必须执行：

```bash
# 检查关键路由是否注册
curl -s http://localhost:5003/api/dev/dashboard -H "Authorization: Bearer $TOKEN" | jq .success
curl -s http://localhost:5003/api/dev/customers -H "Authorization: Bearer $TOKEN" | jq .success
curl -s http://localhost:5003/api/dev/monitor/health -H "Authorization: Bearer $TOKEN" | jq .success
```

### 3. 自愈系统监控（已实现）

自愈系统的异常捕获探针会自动检测 404 错误：

```python
# probe.py 会捕获所有 500 错误并记录告警
# 但 404 错误（HTTPException）不会被捕获，保留 Flask 默认行为
```

**改进建议**：增加 404 监控，对高频 404 路径发送告警。

### 4. 代码提交规范

**重要教训**：
- 所有代码修改必须先 `git commit && git push`
- 部署时使用 `deploy.sh` 自动同步，避免手动 scp 单个文件
- 如果手动更新了某个文件，必须同步更新其他相关文件

---

## 经验总结

### 问题根源
- **流程问题**：手动部署时遗漏了关键文件
- **验证缺失**：部署后没有验证所有功能是否正常

### 改进点
1. ✅ 使用 `deploy.sh` 统一部署，避免手动 scp
2. ✅ 部署后执行验证清单
3. ✅ 所有代码先提交到 git，再从 git 部署
4. ⚠️ 自愈系统需要增加 404 监控（Phase 2 实现）

### 检查清单

**部署前**：
- [ ] 所有代码已提交到 git
- [ ] `deploy.sh` 的 `CORE_FILES` 列表完整
- [ ] 数据库迁移脚本已准备

**部署后**：
- [ ] 后端服务正常启动（检查 `/tmp/backend.log`）
- [ ] 关键 API 返回 200（dashboard, customers, today）
- [ ] 前端页面正常加载数据
- [ ] 企业微信通知正常（测试告警）

---

## 相关文件

- `backend/api.py` - 包含 `/api/dev/` 路由
- `backend/deploy.sh` - 部署脚本
- `miniprogram/pages/customer-admin/` - 客户档案前端
- `miniprogram/api/customer.js` - 客户档案 API 封装

---

**归档人**: AI Assistant  
**审核状态**: 待确认  
**归档日期**: 2026-06-16
