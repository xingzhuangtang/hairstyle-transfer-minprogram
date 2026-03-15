# 通义万相图生图API说明

## API概览

**模型名称**: wan2.5-i2i-preview
**功能**: 通用图像编辑2.5，支持单图编辑、多图融合

## 核心能力

1. **单图编辑** - 基于文本提示词编辑图像
2. **多图融合** - 融合多张参考图生成新图像
3. **风格转换** - 可以通过prompt实现素描等艺术风格转换

## API调用方式

### 认证
- 使用阿里云百炼API Key
- 环境变量: `DASHSCOPE_API_KEY`

### 端点
- 北京地域: `https://dashscope.aliyuncs.com/api/v1`
- 新加坡地域: `https://dashscope-intl.aliyuncs.com/api/v1`

### 调用流程
异步调用,两步式:
1. **创建任务** - 获取task_id
2. **轮询查询** - 根据task_id获取结果

## 关键参数

### 输入参数

```python
{
    "model": "wan2.5-i2i-preview",
    "input": {
        "prompt": "描述期望的编辑效果",  # 必选
        "images": [                       # 必选,最多2张
            "图像URL或Base64"
        ],
        "negative_prompt": "不希望出现的内容"  # 可选
    },
    "parameters": {
        "n": 1,              # 生成图片数量,1-4
        "watermark": false,  # 是否添加水印
        "seed": 12345        # 随机种子
    }
}
```

### 图像输入方式

支持三种方式:
1. **公网URL** - `https://example.com/image.png`
2. **Base64编码** - `data:image/jpeg;base64,{base64_data}`
3. **本地文件** (SDK) - `file:///path/to/image.png`

### 图像限制

- 格式: JPEG、JPG、PNG、BMP、WEBP
- 分辨率: 宽高均在 [384, 5000] 像素
- 文件大小: 不超过10MB
- 输出: 1280×1280 (默认)

## 素描风格生成

### 方法1: 直接在prompt中描述

```python
prompt = "将这张照片转换为铅笔素描风格,保持人物特征"
```

### 方法2: 使用艺术风格描述

```python
prompt = "艺术素描风格,黑白线条,细节丰富,对比强烈"
```

### 方法3: 参考图+风格描述

```python
{
    "prompt": "将图1转换为素描画风格",
    "images": ["原图URL"]
}
```

## Python SDK示例

```python
import dashscope
from dashscope import ImageSynthesis

dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

# 同步调用
rsp = ImageSynthesis.call(
    api_key=api_key,
    model="wan2.5-i2i-preview",
    prompt="将这张照片转换为素描风格",
    images=["图像URL"],
    n=1,
    watermark=False
)

if rsp.status_code == 200:
    result_url = rsp.output.results[0].url
    print(f"生成成功: {result_url}")
```

## 计费说明

- 按**成功生成的图像张数**计费
- 只有`task_status=SUCCEEDED`才计费
- 失败不计费,不消耗免费额度

## 注意事项

1. **URL有效期**: task_id和图像URL均只保留24小时
2. **内容审核**: 输入和输出都会经过内容安全审核
3. **轮询间隔**: 建议10秒查询一次
4. **处理时间**: 通常1-2分钟

## 错误处理

常见错误码:
- `InvalidApiKey` - API Key无效
- `InvalidParameter` - 参数错误
- `DataInspectionFailed` - 内容审核失败
- `InternalError.Timeout` - 处理超时

## 与当前系统集成方案

### 方案1: 替换素描转换模块

将OpenCV素描转换替换为通义万相API:

```python
class BailianSketchConverter:
    def __init__(self, api_key):
        self.api_key = api_key
        dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
    
    def convert_to_sketch(self, image_url, style='pencil'):
        prompts = {
            'pencil': '将这张照片转换为铅笔素描风格,保持人物特征清晰',
            'detailed': '细节丰富的素描画,强调轮廓和阴影',
            'artistic': '艺术素描风格,黑白线条,对比强烈',
            'colored': '彩色素描风格,保留部分颜色,素描线条'
        }
        
        rsp = ImageSynthesis.call(
            api_key=self.api_key,
            model="wan2.5-i2i-preview",
            prompt=prompts.get(style, prompts['pencil']),
            images=[image_url],
            n=1,
            watermark=False
        )
        
        if rsp.status_code == 200:
            return rsp.output.results[0].url
        else:
            raise Exception(f"素描转换失败: {rsp.message}")
```

### 方案2: 五官保持优化

通义万相的图生图可以更好地保持原图特征:

```python
# 在人脸融合后,使用通义万相进行细节优化
prompt = "保持人物五官特征完全一致,只改变发型,不改变脸型、眼睛、鼻子、嘴巴、皱纹等任何面部特征"

rsp = ImageSynthesis.call(
    api_key=api_key,
    model="wan2.5-i2i-preview",
    prompt=prompt,
    images=[融合结果URL, 客户原图URL],  # 双图参考
    n=1
)
```

## 优势

1. **AI大模型** - 比OpenCV算法更智能
2. **艺术效果** - 专业的风格转换
3. **特征保持** - 更好地保持原图特征
4. **灵活控制** - 通过prompt精确控制效果
5. **高质量** - 输出1280×1280高清图像

## 成本

- 免费额度: 查看[模型列表与价格](https://help.aliyun.com/zh/model-studio/models)
- 计费: 按成功生成的图像张数
- 建议: 测试时设置n=1降低成本
