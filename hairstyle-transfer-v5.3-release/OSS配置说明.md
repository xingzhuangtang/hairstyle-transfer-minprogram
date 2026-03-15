# OSS配置说明 - hair-transfer-bucket (上海区域)

## 配置信息

### OSS参数
- **区域**: 上海 (oss-cn-shanghai)
- **Bucket名称**: hair-transfer-bucket
- **Endpoint**: oss-cn-shanghai.aliyuncs.com

### 访问方式
- **公网URL格式**: `https://hair-transfer-bucket.oss-cn-shanghai.aliyuncs.com/{object_name}`
- **对象路径格式**: `hairstyle-transfer/YYYYMMDD/uuid_timestamp.ext`

---

## 前置准备

### 1. 创建OSS Bucket

#### 方式1: 通过控制台创建

1. 访问OSS控制台: https://oss.console.aliyun.com/
2. 点击"创建Bucket"
3. 填写配置:
   - **Bucket名称**: `hair-transfer-bucket`
   - **地域**: 华东2(上海)
   - **存储类型**: 标准存储
   - **读写权限**: 公共读 (推荐) 或 私有 (使用签名URL)
   - **版本控制**: 关闭
   - **服务端加密**: 无
4. 点击"确定"创建

#### 方式2: 通过命令行创建

```bash
# 安装ossutil工具
wget http://gosspublic.alicdn.com/ossutil/1.7.15/ossutil64
chmod 755 ossutil64

# 配置ossutil
./ossutil64 config

# 创建Bucket
./ossutil64 mb oss://hair-transfer-bucket --region cn-shanghai --acl public-read
```

### 2. 配置Bucket权限

#### 公共读权限 (推荐)
- 优点: URL直接可访问,无需签名
- 缺点: 任何人都可以访问
- 适用场景: 临时图像,不涉及隐私

设置方法:
1. 进入Bucket管理页面
2. 点击"权限管理" → "读写权限"
3. 选择"公共读"
4. 点击"保存"

#### 私有权限 + 签名URL (更安全)
- 优点: 更安全,可控制访问时间
- 缺点: URL包含签名,较长
- 适用场景: 涉及隐私的图像

设置方法:
1. 保持Bucket为"私有"权限
2. 使用代码中的签名URL方式:

```python
# 在 app_aliyun.py 的 upload_to_oss 函数中
# 将第125行改为:
signed_url = bucket.sign_url('GET', object_name, 3600)  # 有效期3600秒
return signed_url
```

### 3. 配置跨域访问 (CORS)

如果前端需要直接访问OSS,需要配置CORS:

1. 进入Bucket管理页面
2. 点击"权限管理" → "跨域设置"
3. 点击"创建规则"
4. 填写配置:
   - **来源**: `*` (或指定域名)
   - **允许Methods**: GET, POST, PUT, DELETE, HEAD
   - **允许Headers**: `*`
   - **暴露Headers**: ETag, x-oss-request-id
   - **缓存时间**: 600
5. 点击"确定"

---

## 安装依赖

### 安装oss2库

```bash
pip3 install oss2
```

### 更新requirements.txt

在 `requirements_new.txt` 中添加:
```
oss2>=2.17.0
```

---

## 代码已集成

### upload_to_oss 函数已更新

`app_aliyun.py` 中的 `upload_to_oss` 函数已经完整实现,配置信息:

```python
# OSS配置
endpoint = 'oss-cn-shanghai.aliyuncs.com'  # 上海区域
bucket_name = 'hair-transfer-bucket'        # Bucket名称
```

### 功能特性

1. **自动生成唯一文件名**
   - 格式: `hairstyle-transfer/YYYYMMDD/uuid_timestamp.ext`
   - 示例: `hairstyle-transfer/20251104/a1b2c3d4_1730678400.jpg`

2. **完善的错误处理**
   - Bucket不存在
   - 访问权限不足
   - 网络错误
   - 未安装oss2库

3. **详细的日志输出**
   - 上传进度提示
   - 对象名称显示
   - 公网URL输出

4. **支持两种URL模式**
   - 公共读: 直接URL
   - 私有: 签名URL

---

## 使用方法

### 1. 设置环境变量

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID='your-access-key-id'
export ALIBABA_CLOUD_ACCESS_KEY_SECRET='your-access-key-secret'
```

### 2. 创建Bucket

确保已创建名为 `hair-transfer-bucket` 的Bucket,地域为上海。

### 3. 启动应用

```bash
cd hairstyle-transfer
./start_aliyun.sh
```

### 4. 测试上传

访问 http://localhost:5002,上传图像测试。

---

## 测试OSS连接

### 使用测试脚本

```bash
cd hairstyle-transfer
python3 oss_upload_complete.py
```

测试脚本会:
1. 检查AccessKey配置
2. 测试Bucket访问
3. 列出已有对象
4. 显示Bucket信息

### 预期输出

```
============================================================
测试OSS连接
============================================================
✅ AccessKey ID: LTAI5t...
✅ Endpoint: oss-cn-shanghai.aliyuncs.com
✅ Bucket: hair-transfer-bucket

🔍 测试Bucket访问...
✅ Bucket访问成功!
   创建时间: 2025-11-04 12:00:00+08:00
   存储类型: Standard
   访问权限: public-read

📋 列出对象...
   (暂无对象)

✅ OSS连接测试成功!
```

---

## 常见问题

### Q1: Bucket不存在?
**A**: 请先创建Bucket:
```bash
# 通过控制台: https://oss.console.aliyun.com/
# 或使用ossutil命令行工具
```

### Q2: 访问被拒绝?
**A**: 检查:
1. AccessKey是否正确
2. RAM用户是否有OSS权限
3. Bucket是否在当前账号下

### Q3: 上传成功但无法访问URL?
**A**: 检查Bucket权限:
- 如果是私有权限,需要使用签名URL
- 如果是公共读,检查URL是否正确

### Q4: 图像URL阿里云API无法访问?
**A**: 确保:
1. Bucket设置为公共读
2. URL格式正确
3. 对象已成功上传
4. 网络连接正常

### Q5: 如何查看已上传的文件?
**A**: 
- 方式1: OSS控制台 → 选择Bucket → 文件管理
- 方式2: 运行测试脚本查看列表

---

## 文件组织结构

### OSS中的目录结构

```
hair-transfer-bucket/
└── hairstyle-transfer/
    ├── 20251104/
    │   ├── a1b2c3d4_1730678400.jpg  (发型参考图)
    │   ├── b2c3d4e5_1730678401.jpg  (客户照片)
    │   └── c3d4e5f6_1730678450.png  (处理结果)
    ├── 20251105/
    │   └── ...
    └── ...
```

### 文件命名规则

- **日期目录**: YYYYMMDD格式
- **文件名**: `{uuid}_{timestamp}.{ext}`
- **UUID**: 8位随机字符
- **时间戳**: Unix时间戳
- **扩展名**: 保持原文件扩展名

---

## 成本估算

### OSS费用构成

1. **存储费用**
   - 标准存储: ¥0.12/GB/月
   - 示例: 1000张图片(每张2MB) = 2GB ≈ ¥0.24/月

2. **流量费用**
   - 外网流出: ¥0.50/GB
   - 示例: 1000次下载(每次2MB) = 2GB ≈ ¥1.00

3. **请求费用**
   - PUT请求: ¥0.01/万次
   - GET请求: ¥0.01/万次
   - 示例: 1000次上传+下载 ≈ ¥0.002

### 成本控制建议

1. **定期清理**
   - 设置生命周期规则
   - 自动删除30天前的文件

2. **使用CDN**
   - 降低流量费用
   - 提升访问速度

3. **压缩图像**
   - 减少存储空间
   - 降低流量消耗

---

## 高级配置

### 1. 设置生命周期规则

自动删除过期文件:

```python
import oss2
from oss2.models import LifecycleRule, LifecycleExpiration

auth = oss2.Auth('your-key-id', 'your-key-secret')
bucket = oss2.Bucket(auth, 'oss-cn-shanghai.aliyuncs.com', 'hair-transfer-bucket')

# 创建生命周期规则
rule = LifecycleRule(
    'delete-after-30-days',
    'hairstyle-transfer/',
    status=LifecycleRule.ENABLED,
    expiration=LifecycleExpiration(days=30)
)

lifecycle = oss2.models.BucketLifecycle([rule])
bucket.put_bucket_lifecycle(lifecycle)
```

### 2. 启用CDN加速

1. 开通CDN服务
2. 添加加速域名
3. 配置CNAME
4. 更新代码中的URL

### 3. 图像处理

OSS支持实时图像处理:

```python
# 生成缩略图URL
thumbnail_url = f'{public_url}?x-oss-process=image/resize,w_200,h_200'

# 添加水印
watermark_url = f'{public_url}?x-oss-process=image/watermark,text_SGFpclRyYW5zZmVy'
```

---

## 安全建议

### 1. 使用RAM子账号
- 不要使用主账号AccessKey
- 创建专用RAM用户
- 授予最小权限

### 2. 定期轮换密钥
- 每3-6个月更换AccessKey
- 使用密钥管理服务(KMS)

### 3. 启用日志审计
- 开启OSS访问日志
- 监控异常访问
- 设置告警规则

### 4. 配置防盗链
- 设置Referer白名单
- 防止资源被盗用

---

## 参考资源

### 官方文档
- [OSS产品文档](https://help.aliyun.com/product/31815.html)
- [OSS Python SDK](https://help.aliyun.com/document_detail/32026.html)
- [OSS定价](https://www.aliyun.com/price/product#/oss/detail)

### 工具下载
- [ossutil命令行工具](https://help.aliyun.com/document_detail/120075.html)
- [ossbrowser图形化工具](https://help.aliyun.com/document_detail/61872.html)

---

**OSS配置完成后,系统即可正常使用!** ✅
