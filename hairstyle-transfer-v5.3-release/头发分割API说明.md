# 阿里云头发分割API说明

## API信息

**API名称**: SegmentHair
**类目**: 分割抠图（imageseg）
**功能**: 识别图像中的人物头像，对人物头像区域进行抠图解析，输出PNG格式的人物头发矩形透明图

## 输入限制

- 图像格式：JPEG、JPG、PNG、BMP
- 图像大小：不超过3M
- 图像分辨率：大于32×32像素，小于2000×2000像素
- URL地址中不能包含中文字符

## 请求参数

- **ImageURL**: 图像URL地址

## 返回数据

```json
{
  "RequestId": "D6C24839-91A7-41DA-B31F-98F08EF80CC0",
  "Data": {
    "Elements": [{
      "ImageURL": "http://viapi-cn-shanghai-dha-segmenter.oss-cn-shanghai.aliyuncs.com/...",
      "Width": 113,
      "Height": 180,
      "Y": 102,
      "X": 446
    }]
  }
}
```

## SDK调用

使用阿里云SDK调用，选择AI类目为**分割抠图（imageseg）**的SDK包

## 应用场景

1. **假发网络试戴**: 通过头发分割，截取自拍照的头发后，换成假发图像
2. **理发店发型尝试**: 发型师指导客户拍摄头像，换成各种发型

## 特色优势

**发丝边缘的精确分割**: 对发丝边缘可以精确分割，分割后图像编辑结果无违和感

## 计费

按调用次数计费，详见阿里云官网定价
