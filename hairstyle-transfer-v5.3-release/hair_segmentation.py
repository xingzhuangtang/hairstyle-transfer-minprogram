#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云头发分割模块
使用SegmentHair API提取头发区域，返回透明背景的头发图
"""

import os
import requests
from alibabacloud_imageseg20191230.client import Client as ImagesegClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_imageseg20191230 import models as imageseg_models
from alibabacloud_tea_util import models as util_models


class HairSegmentation:
    """头发分割类"""
    
    def __init__(self):
        """初始化头发分割服务"""
        # 从环境变量获取AccessKey
        access_key_id = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
        access_key_secret = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        
        if not access_key_id or not access_key_secret:
            raise ValueError("未设置阿里云AccessKey环境变量")
        
        # 创建配置
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint='imageseg.cn-shanghai.aliyuncs.com'
        )
        
        # 创建客户端
        self.client = ImagesegClient(config)
        
        print("✅ 头发分割服务初始化成功")
        print(f"   AccessKey ID: {access_key_id[:10]}...")
        print(f"   地域: cn-shanghai")
    
    def segment_hair(self, image_url):
        """
        分割头发
        
        Args:
            image_url: 图像URL地址（必须是公网可访问的URL）
        
        Returns:
            dict: {
                'success': bool,
                'hair_url': str,  # 透明背景的头发图URL
                'width': int,
                'height': int,
                'x': int,
                'y': int,
                'message': str
            }
        """
        try:
            print("\n" + "="*60)
            print("🚀 开始头发分割")
            print("="*60)
            print(f"\n📋 输入图像: {image_url[:80]}...")
            
            # 创建请求
            request = imageseg_models.SegmentHairRequest(
                image_url=image_url
            )
            
            runtime = util_models.RuntimeOptions()
            
            # 调用API
            print("\n📤 调用SegmentHair API...")
            response = self.client.segment_hair_with_options(request, runtime)
            
            # 解析结果
            if response.body.data and response.body.data.elements:
                element = response.body.data.elements[0]
                
                result = {
                    'success': True,
                    'hair_url': element.image_url,
                    'width': element.width,
                    'height': element.height,
                    'x': element.x,
                    'y': element.y,
                    'message': '头发分割成功'
                }
                
                print("\n✅ 头发分割成功!")
                print(f"   头发图URL: {result['hair_url'][:80]}...")
                print(f"   尺寸: {result['width']}x{result['height']}")
                print(f"   位置: ({result['x']}, {result['y']})")
                print("\n" + "="*60)
                
                return result
            else:
                return {
                    'success': False,
                    'message': 'API返回数据为空'
                }
        
        except Exception as e:
            error_msg = f"头发分割失败: {str(e)}"
            print(f"\n❌ {error_msg}")
            print("="*60)
            
            return {
                'success': False,
                'message': error_msg
            }
    
    def download_hair_image(self, hair_url, save_path):
        """
        下载头发图像
        
        Args:
            hair_url: 头发图URL
            save_path: 保存路径
        
        Returns:
            bool: 是否成功
        """
        try:
            print(f"\n💾 下载头发图像...")
            print(f"   URL: {hair_url[:80]}...")
            print(f"   保存到: {save_path}")
            
            # 下载图像
            response = requests.get(hair_url, timeout=30)
            response.raise_for_status()
            
            # 保存到文件
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            # 检查文件大小
            file_size = os.path.getsize(save_path) / 1024  # KB
            
            print(f"✅ 头发图像已保存")
            print(f"   文件大小: {file_size:.1f}KB")
            
            return True
        
        except Exception as e:
            print(f"❌ 下载头发图像失败: {str(e)}")
            return False


def test_hair_segmentation():
    """测试头发分割功能"""
    print("\n" + "="*60)
    print("测试头发分割功能")
    print("="*60)
    
    try:
        # 创建头发分割器
        segmenter = HairSegmentation()
        
        # 测试图像URL（需要替换为实际的图像URL）
        test_url = "https://hair-transfer-bucket.oss-cn-shanghai.aliyuncs.com/test/sample.jpg"
        
        # 分割头发
        result = segmenter.segment_hair(test_url)
        
        if result['success']:
            print("\n✅ 测试成功!")
            print(f"   头发图URL: {result['hair_url']}")
            
            # 下载头发图像
            save_path = "static/test_hair.png"
            segmenter.download_hair_image(result['hair_url'], save_path)
        else:
            print(f"\n❌ 测试失败: {result['message']}")
    
    except Exception as e:
        print(f"\n❌ 测试异常: {str(e)}")


if __name__ == '__main__':
    test_hair_segmentation()
