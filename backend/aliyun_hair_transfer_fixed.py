#!/usr/bin/env python3
"""
阿里云发型迁移模块 - 修复版
使用人脸融合API实现发型迁移(不使用头发分割)
"""

import os
import sys
import time
import requests
from typing import Optional, Tuple
import cv2
import numpy as np

# 阿里云SDK导入
from alibabacloud_facebody20191230.client import Client as FaceBodyClient
from alibabacloud_facebody20191230 import models as facebody_models
from alibabacloud_tea_openapi import models as open_api_models

# 导入自定义模块(容错)
try:
    from image_preprocessor import ImagePreprocessor
    PREPROCESSOR_AVAILABLE = True
except ImportError as e:
    PREPROCESSOR_AVAILABLE = False
    ImagePreprocessor = None
    print(f"⚠️  图像预处理模块不可用: {e}")

# 优先使用百炼素描转换器
try:
    from bailian_sketch_converter import BailianSketchConverter
    BAILIAN_SKETCH_AVAILABLE = True
    print("✅ 百炼素描转换器可用")
except ImportError as e:
    BAILIAN_SKETCH_AVAILABLE = False
    BailianSketchConverter = None
    print(f"⚠️  百炼素描转换器不可用: {e}")

# 备用: OpenCV素描转换器
try:
    from sketch_converter import SketchConverter
    OPENCV_SKETCH_AVAILABLE = True
    print("✅ OpenCV素描转换器可用(备用)")
except ImportError as e:
    OPENCV_SKETCH_AVAILABLE = False
    SketchConverter = None
    print(f"⚠️  OpenCV素描转换器不可用: {e}")

SKETCH_AVAILABLE = BAILIAN_SKETCH_AVAILABLE or OPENCV_SKETCH_AVAILABLE


class AliyunHairTransferFixed:
    """阿里云发型迁移服务 - 修复版"""
    
    def __init__(
        self,
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        region: str = 'cn-shanghai'
    ):
        """
        初始化阿里云发型迁移服务
        
        Args:
            access_key_id: 阿里云AccessKey ID
            access_key_secret: 阿里云AccessKey Secret
            region: 地域,默认上海
        """
        # 获取AccessKey
        self.access_key_id = access_key_id or os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
        self.access_key_secret = access_key_secret or os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        
        if not self.access_key_id or not self.access_key_secret:
            raise ValueError(
                "未设置阿里云AccessKey! 请设置环境变量:\n"
                "export ALIBABA_CLOUD_ACCESS_KEY_ID='your-key-id'\n"
                "export ALIBABA_CLOUD_ACCESS_KEY_SECRET='your-key-secret'"
            )
        
        self.region = region
        
        # 创建人脸人体客户端
        self.facebody_client = self._create_facebody_client()
        
        # 创建工具实例(如果可用)
        if PREPROCESSOR_AVAILABLE:
            self.preprocessor = ImagePreprocessor()
        else:
            self.preprocessor = None
        
        # 初始化素描转换器(优先百炼)
        if BAILIAN_SKETCH_AVAILABLE:
            try:
                self.bailian_sketch = BailianSketchConverter()
                self.sketch_converter = None
                print("✅ 使用百炼素描转换器")
            except Exception as e:
                print(f"⚠️  百炼素描初始化失败: {e}")
                self.bailian_sketch = None
                if OPENCV_SKETCH_AVAILABLE:
                    self.sketch_converter = SketchConverter()
                    print("✅ 降级使用OpenCV素描转换器")
                else:
                    self.sketch_converter = None
        elif OPENCV_SKETCH_AVAILABLE:
            self.bailian_sketch = None
            self.sketch_converter = SketchConverter()
            print("✅ 使用OpenCV素描转换器")
        else:
            self.bailian_sketch = None
            self.sketch_converter = None
        
        print(f"✅ 初始化阿里云发型迁移服务(修复版)")
        print(f"   AccessKey ID: {self.access_key_id[:8]}...")
        print(f"   地域: {self.region}")
    
    def _create_facebody_client(self) -> FaceBodyClient:
        """创建人脸人体客户端"""
        config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
            endpoint=f'facebody.{self.region}.aliyuncs.com'
        )
        return FaceBodyClient(config)
    
    def add_face_template(self, image_url: str) -> str:
        """
        添加人脸融合模板
        
        Args:
            image_url: 模板图像URL(发型参考图的完整图像)
        
        Returns:
            template_id: 模板ID
        """
        print(f"\n📋 步骤1: 创建人脸融合模板")
        print(f"   模板图像: {image_url[:50]}...")
        
        try:
            # 创建请求
            request = facebody_models.AddFaceImageTemplateRequest(
                image_url=image_url
            )
            
            # 调用API
            response = self.facebody_client.add_face_image_template(request)
            
            # 检查响应
            if not response.body or not response.body.data:
                raise Exception("API返回数据为空")
            
            template_id = response.body.data.template_id
            
            print(f"✅ 模板创建成功")
            print(f"   模板ID: {template_id}")
            
            return template_id
            
        except Exception as e:
            print(f"❌ 模板创建失败: {e}")
            raise
    
    def merge_face(
        self,
        template_id: str,
        user_image_url: str,
        model_version: str = 'v1',
        add_watermark: bool = False
    ) -> str:
        """
        人脸融合
        
        Args:
            template_id: 模板ID
            user_image_url: 用户人脸图像URL(客户照片)
            model_version: 模型版本,v1(脸型适配)或v2(非脸型适配)
            add_watermark: 是否添加水印
        
        Returns:
            result_url: 融合后的图像URL
        """
        print(f"\n🎨 步骤2: 人脸融合")
        print(f"   模板ID: {template_id}")
        print(f"   用户图像: {user_image_url[:50]}...")
        print(f"   模型版本: {model_version}")
        
        try:
            # 创建请求
            request = facebody_models.MergeImageFaceRequest(
                template_id=template_id,
                image_url=user_image_url,
                model_version=model_version,
                add_watermark=add_watermark
            )
            
            # 调用API
            response = self.facebody_client.merge_image_face(request)
            
            # 检查响应
            if not response.body or not response.body.data:
                raise Exception("API返回数据为空")
            
            result_url = response.body.data.image_url
            
            print(f"✅ 人脸融合成功")
            print(f"   结果URL: {result_url[:50]}...")
            
            return result_url
            
        except Exception as e:
            print(f"❌ 人脸融合失败: {e}")
            raise
    
    def download_image(self, url: str, save_path: Optional[str] = None, max_retries: int = 5) -> np.ndarray:
        """
        下载图像（带重试机制）
        
        Args:
            url: 图像URL
            save_path: 保存路径(可选)
            max_retries: 最大重试次数
        
        Returns:
            image: OpenCV格式的图像数组
        """
        print(f"\n💾 下载图像")
        print(f"   URL: {url[:50]}...")
        
        for attempt in range(max_retries):
            try:
                print(f"   尝试 {attempt + 1}/{max_retries}...")
                
                # 下载图像 - 增加超时时间和流式下载
                response = requests.get(url, timeout=120, stream=True)
                response.raise_for_status()
                
                # 检查响应大小
                if 'Content-Length' in response.headers:
                    content_length = int(response.headers.get('Content-Length', 0))
                    if content_length == 0:
                        raise ValueError("服务器返回空内容")
                    print(f"   预期大小: {content_length/1024:.1f}KB")
                
                # 转换为OpenCV格式
                image_array = np.frombuffer(response.content, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_UNCHANGED)

                if image is None:
                    raise Exception("图像解码失败")

                # 验证图像尺寸是否合理（防止空图或异常图）
                h, w = image.shape[:2]
                if h < 10 or w < 10:
                    raise Exception(f"图像尺寸异常: {w}x{h}，可能不是有效图片")

                if len(image.shape) < 2:
                    raise Exception(f"图像格式异常，shape: {image.shape}")

                print(f"   图像尺寸: {w}x{h}, 通道数: {len(image.shape)}")

                # 保存到本地
                if save_path:
                    write_success = cv2.imwrite(save_path, image)

                    # 验证文件是否真正写入成功
                    if not write_success or not os.path.exists(save_path):
                        raise Exception(f"文件保存失败: cv2.imwrite返回{write_success}, 文件存在{os.path.exists(save_path)}")

                    file_size = os.path.getsize(save_path)
                    if file_size == 0:
                        raise Exception(f"保存的文件为空: {save_path}")

                    print(f"✅ 图像下载成功")
                    print(f"   文件大小: {file_size/1024:.1f}KB")
                    print(f"   保存路径: {save_path}")
                else:
                    print(f"✅ 图像下载成功: {image.shape}")

                return image
            
            except Exception as e:
                print(f"❌ 下载失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                
                # 如果文件存在，删除它
                if save_path and os.path.exists(save_path):
                    try:
                        os.remove(save_path)
                    except:
                        pass
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避：2, 4, 8秒
                    print(f"   等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
        
        print(f"❌ 图像下载最终失败")
        raise Exception(f"下载图像失败，已重试{max_retries}次")
    
    def transfer_hairstyle(
        self,
        hairstyle_image_url: str,
        customer_image_url: str,
        model_version: str = 'v1',
        face_blend_ratio: float = 0.5,
        save_dir: Optional[str] = None,
        enable_sketch: bool = False,
        sketch_style: str = 'artistic'
    ) -> Tuple[np.ndarray, dict]:
        """
        完整的发型迁移流程(修复版)
        
        流程说明:
        1. 使用发型参考图(完整图像)创建模板
        2. 将客户人脸融合到模板图
        3. 结果是客户人脸 + 发型参考图的发型
        4. (可选)转换为素描效果
        
        Args:
            hairstyle_image_url: 发型参考图URL(完整图像)
            customer_image_url: 客户照片URL
            model_version: 模型版本(v1=脸型适配, v2=非脸型适配)
            face_blend_ratio: 脸型融合权重(0=偏向客户脸型, 1=偏向发型脸型)
            save_dir: 保存目录(可选)
            enable_sketch: 是否启用素描效果
            sketch_style: 素描风格(pencil/detailed/artistic/color)
        
        Returns:
            (result_image, info): 结果图像和处理信息
        """
        print(f"\n" + "="*60)
        print(f"🚀 开始发型迁移(修复版)")
        print(f"="*60)
        print(f"\n💡 流程说明:")
        print(f"   1. 使用发型参考图创建模板(完整图像,包含人脸)")
        print(f"   2. 将客户人脸融合到模板图")
        print(f"   3. 结果: 客户人脸 + 发型参考图的发型")
        
        info = {
            'start_time': time.time(),
            'hairstyle_url': hairstyle_image_url,
            'customer_url': customer_image_url
        }
        
        try:
            # 步骤1: 创建模板(使用完整的发型参考图)
            template_id = self.add_face_template(hairstyle_image_url)
            info['template_id'] = template_id
            
            # 步骤2: 人脸融合(将客户人脸融合到模板)
            result_url = self.merge_face(
                template_id=template_id,
                user_image_url=customer_image_url,
                model_version=model_version
            )
            info['result_url'] = result_url
            
            # 步骤3: 下载结果
            save_path = None
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                timestamp = int(time.time())
                save_path = os.path.join(save_dir, f'result_{timestamp}.png')
            
            result_image = self.download_image(result_url, save_path)
            info['save_path'] = save_path
            
            # 步骤4: 素描效果(可选)
            if enable_sketch and SKETCH_AVAILABLE:
                print(f"\n🎨 步骤4: 素描效果转换")
                
                # 优先使用百炼素描转换器
                if self.bailian_sketch:
                    try:
                        print(f"   使用: 百炼大模型素描转换")
                        
                        # 百炼需要稳定图像，使用本地文件路径避免临时URL问题
                        sketch_url, sketch_info = self.bailian_sketch.convert(
                            image_url=result_url,
                            style=sketch_style,
                            local_file_path=save_path  # 传递本地文件路径
                        )
                        
                        if sketch_info['success']:
                            # 下载素描结果 - 使用增强的下载功能
                            result_image = self.download_image(sketch_url, max_retries=5)

                            # 保存素描版本
                            if save_path:
                                sketch_path = save_path.replace('.png', '_sketch.png')
                                write_success = cv2.imwrite(sketch_path, result_image)

                                # 验证文件是否真正写入成功
                                if not write_success or not os.path.exists(sketch_path):
                                    raise Exception(f"素描文件保存失败: {sketch_path} (cv2.imwrite返回{write_success}, 文件存在{os.path.exists(sketch_path)})")

                                file_size = os.path.getsize(sketch_path)
                                if file_size == 0:
                                    raise Exception(f"素描文件为空: {sketch_path}")

                                info['sketch_path'] = sketch_path
                                print(f"✅ 素描版本已保存: {sketch_path} ({file_size} bytes)")

                            info['sketch_enabled'] = True
                            info['sketch_method'] = 'bailian'
                            info['sketch_style'] = sketch_style
                            info['sketch_info'] = sketch_info
                        else:
                            raise Exception(sketch_info.get('error', '未知错误'))
                            
                    except Exception as e:
                        print(f"⚠️  百炼素描转换失败: {e}")
                        
                        # 降级使用OpenCV
                        if self.sketch_converter:
                            print(f"   降级使用OpenCV素描转换")
                            try:
                                result_image = self.sketch_converter.convert(
                                    result_image,
                                    style=sketch_style
                                )

                                if save_path:
                                    sketch_path = save_path.replace('.png', '_sketch.png')
                                    write_success = cv2.imwrite(sketch_path, result_image)

                                    # 验证文件是否真正写入成功
                                    if not write_success or not os.path.exists(sketch_path):
                                        raise Exception(f"OpenCV素描文件保存失败: {sketch_path}")

                                    file_size = os.path.getsize(sketch_path)
                                    if file_size == 0:
                                        raise Exception(f"OpenCV素描文件为空: {sketch_path}")

                                    info['sketch_path'] = sketch_path
                                    print(f"✅ OpenCV素描版本已保存: {sketch_path} ({file_size} bytes)")

                                    info['sketch_enabled'] = True
                                    info['sketch_method'] = 'opencv'
                                    info['sketch_style'] = sketch_style
                            except Exception as e2:
                                print(f"⚠️  OpenCV素描也失败: {e2}")
                                info['sketch_enabled'] = False
                                info['sketch_error'] = f"Bailian: {e}, OpenCV: {e2}"
                        else:
                            info['sketch_enabled'] = False
                            info['sketch_error'] = str(e)
                
                # 只有OpenCV素描转换器
                elif self.sketch_converter:
                    try:
                        print(f"   使用: OpenCV素描转换")
                        result_image = self.sketch_converter.convert(
                            result_image,
                            style=sketch_style
                        )

                        if save_path:
                            sketch_path = save_path.replace('.png', '_sketch.png')
                            write_success = cv2.imwrite(sketch_path, result_image)

                            # 验证文件是否真正写入成功
                            if not write_success or not os.path.exists(sketch_path):
                                raise Exception(f"素描文件保存失败: {sketch_path}")

                            file_size = os.path.getsize(sketch_path)
                            if file_size == 0:
                                raise Exception(f"素描文件为空: {sketch_path}")

                            info['sketch_path'] = sketch_path
                            print(f"✅ 素描版本已保存: {sketch_path} ({file_size} bytes)")

                            info['sketch_enabled'] = True
                            info['sketch_method'] = 'opencv'
                            info['sketch_style'] = sketch_style
                        else:
                            info['sketch_enabled'] = False
                            info['sketch_error'] = 'save_path is None'
                    except Exception as e:
                        print(f"⚠️  素描转换失败: {e}")
                        info['sketch_enabled'] = False
                        info['sketch_error'] = str(e)
                
                else:
                    print(f"⚠️  没有可用的素描转换器")
                    info['sketch_enabled'] = False
                    info['sketch_skipped'] = True
            
            elif enable_sketch and not SKETCH_AVAILABLE:
                print(f"\n⚠️  素描模块不可用,跳过素描转换")
                info['sketch_enabled'] = False
                info['sketch_skipped'] = True
            else:
                info['sketch_enabled'] = False
            
            # 计算耗时
            info['elapsed_time'] = time.time() - info['start_time']
            
            print(f"\n" + "="*60)
            print(f"🎉 发型迁移完成!")
            print(f"   总耗时: {info['elapsed_time']:.2f}秒")
            if save_path:
                print(f"   结果保存: {save_path}")
            print(f"="*60)
            
            return result_image, info
            
        except Exception as e:
            info['error'] = str(e)
            info['elapsed_time'] = time.time() - info['start_time']
            print(f"\n" + "="*60)
            print(f"❌ 发型迁移失败: {e}")
            print(f"   总耗时: {info['elapsed_time']:.2f}秒")
            print(f"="*60)
            raise


def main():
    """测试函数"""
    print("阿里云发型迁移模块 - 修复版")
    print("="*60)
    
    # 检查环境变量
    if not os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID'):
        print("❌ 未设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID")
        print("\n请设置:")
        print("export ALIBABA_CLOUD_ACCESS_KEY_ID='your-key-id'")
        print("export ALIBABA_CLOUD_ACCESS_KEY_SECRET='your-key-secret'")
        sys.exit(1)
    
    # 创建服务实例
    try:
        service = AliyunHairTransferFixed()
        print("\n✅ 服务初始化成功")
        print("\n使用示例:")
        print("```python")
        print("service = AliyunHairTransferFixed()")
        print("result, info = service.transfer_hairstyle(")
        print("    hairstyle_image_url='http://your-oss/hairstyle.jpg',")
        print("    customer_image_url='http://your-oss/customer.jpg'")
        print(")")
        print("```")
        print("\n⚠️  注意:")
        print("   - 发型参考图使用完整图像(不进行头发分割)")
        print("   - 模板图必须包含完整的人脸")
        print("   - 结果是客户人脸融合到发型参考图")
    except Exception as e:
        print(f"\n❌ 服务初始化失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
