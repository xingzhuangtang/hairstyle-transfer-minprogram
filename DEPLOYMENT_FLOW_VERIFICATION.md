# 小程序部署流程验证

## 完整部署流程

### 1. 后端部署（deploy.sh）

```bash
# 本地执行
cd backend && ./deploy.sh test --force
```

**流程：**
1. 本地 `backend/` 目录下的文件
2. 通过 SCP 上传到服务器 `/opt/hairstyle-transfer-v5.3-release/backend/`
3. 服务器重启服务：`cd /opt/.../backend && python3 app.py`

**路径映射：**
```
本地: /Users/tangxingzhuang/5.3_server/backend/
  ↓ (deploy.sh 同步)
服务器: /opt/hairstyle-transfer-v5.3-release/backend/
```

### 2. 前端部署（微信开发者工具）

**流程：**
1. 本地 `miniprogram/` 目录
2. 微信开发者工具打开 `miniprogram/` 项目
3. 点击"上传"按钮，上传到微信后台
4. 微信官方审核
5. 审核通过后发布

**关键配置：**
- `miniprogram/utils/constants.js` 中的 `API_BASE_URL`
- 必须指向生产域名：`https://xn--gmq63iba0780e.com`
- 小程序会请求这个域名，由 Nginx 转发到后端服务

## 路径匹配验证

### ✅ 后端路径（已修复）

| 位置 | 路径 | 状态 |
|---|---|---|
| deploy.sh 同步目标 | `$DEPLOY_PATH/backend/` | ✅ 正确 |
| deploy.sh 服务启动 | `cd $DEPLOY_PATH/backend && python3 app.py` | ✅ 正确 |
| deploy.sh .env 检查 | `$DEPLOY_PATH/backend/.env` | ✅ 已修复 |
| 服务器实际运行 | `/opt/.../backend/app.py` | ✅ 正确 |

### ✅ 前端路径

| 位置 | 配置 | 状态 |
|---|---|---|
| API_BASE_URL | `https://xn--gmq63iba0780e.com` | ✅ 已修复 |
| Nginx 转发 | 域名 → `127.0.0.1:5003` | ✅ 正确 |

## 新功能上线流程测试

### 场景：给小程序增加新功能

**步骤 1：本地开发**
```bash
# 修改后端代码
vim backend/api.py  # 添加新接口

# 修改前端代码
vim miniprogram/pages/index/index.js  # 调用新接口
```

**步骤 2：部署后端**
```bash
cd backend && ./deploy.sh test --force
```

**验证：**
- ✅ 代码同步到 `/opt/.../backend/`
- ✅ 服务重启，运行新代码
- ✅ 新接口可通过域名访问

**步骤 3：上传小程序**
1. 打开微信开发者工具
2. 上传 `miniprogram/` 项目
3. 填写版本号和备注
4. 提交审核

**步骤 4：微信审核**
- 等待微信官方审核（通常 1-7 天）
- 审核通过后，点击"发布"

**步骤 5：客户使用**
- 客户打开小程序，自动更新到新版本
- 前端调用新接口 → 请求 `https://xn--gmq63iba0780e.com/api/xxx`
- Nginx 转发到后端 → 后端返回新数据
- ✅ 客户可以使用新功能

## 关键检查点

### 1. 后端代码一致性

**检查服务器运行的代码是否是最新的：**
```bash
# 本地
md5 backend/api.py

# 服务器
ssh root@139.196.105.33 "md5sum /opt/.../backend/api.py"
```

**如果不一致：**
- 重新执行 `./deploy.sh test --force`
- 检查 deploy.sh 的同步日志

### 2. 前端 API_BASE_URL

**检查小程序请求的域名：**
```bash
# 本地
grep "API_BASE_URL" miniprogram/utils/constants.js
```

**必须输出：**
```javascript
export const API_BASE_URL = "https://xn--gmq63iba0780e.com"
```

**如果是测试 IP（如 `http://192.168.3.189:5003`）：**
- 客户无法访问（内网 IP）
- 需要修改为生产域名并重新上传小程序

### 3. 微信开发者工具上传

**检查上传状态：**
1. 登录微信公众平台：https://mp.weixin.qq.com
2. 进入"版本管理"
3. 查看"开发版本"是否有最新上传
4. 确认版本号和上传时间

## 常见问题

### Q1: 部署后客户还是用旧功能？

**可能原因：**
1. ❌ 小程序未上传或未发布
   - 解决：在微信开发者工具上传，等待审核发布
   
2. ❌ API_BASE_URL 指向测试 IP
   - 解决：修改为生产域名，重新上传小程序

3. ❌ 后端未重启
   - 解决：检查 deploy.sh 日志，确认服务已重启

4. ❌ 客户缓存
   - 解决：让客户删除小程序重新进入

### Q2: 服务器上的代码和本地不一样？

**排查步骤：**
1. 检查 deploy.sh 是否执行成功
2. 检查 SCP 同步日志
3. 对比本地和服务器文件 MD5
4. 重新执行部署

### Q3: 新功能接口返回 404？

**可能原因：**
1. ❌ 后端未部署新代码
   - 解决：重新执行 deploy.sh

2. ❌ 路由未注册
   - 解决：检查 api.py 中的路由定义

3. ❌ Nginx 配置问题
   - 解决：检查 Nginx 转发规则

## 总结

✅ **正确的部署流程：**
1. 本地开发 → 2. deploy.sh 部署后端 → 3. 微信开发者工具上传前端 → 4. 微信审核发布 → 5. 客户使用

✅ **路径匹配：**
- 后端：`backend/` → `/opt/.../backend/`（已修复）
- 前端：`API_BASE_URL` → 生产域名（已修复）

✅ **新功能上线：**
- 后端代码通过 deploy.sh 同步
- 前端代码通过微信开发者工具上传
- 两者独立，但通过 API_BASE_URL 连接
- 客户使用新版本需要前端发布后才会生效
