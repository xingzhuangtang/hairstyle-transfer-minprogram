#!/usr/bin/env python3
"""
图像预处理模块
自动调整图像大小和分辨率,满足阿里云API要求
"""

import os
import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional


class ImagePreprocessor:
    """图像预处理器"""
    
    # 阿里云API限制
    MAX_FILE_SIZE = 3 * 1024 * 1024  # 3MB
    MIN_RESOLUTION = 32  # 最小分辨率
    MAX_RESOLUTION = 2000  # 最大分辨率
    
    def __init__(self):
        """初始化预处理器"""
        pass
    
    def get_file_size(self, file_path: str) -> int:
        """
        获取文件大小(字节)
        
        Args:
            file_path: 文件路径
        
        Returns:
            size: 文件大小(字节)
        """
        return os.path.getsize(file_path)
    
    def get_image_resolution(self, image: np.ndarray) -> Tuple[int, int]:
        """
        获取图像分辨率
        
        Args:
            image: OpenCV图像
        
        Returns:
            (width, height): 图像分辨率
        """
        height, width = image.shape[:2]
        return width, height
    
    def calculate_target_size(
        self,
        width: int,
        height: int,
        max_size: int = MAX_RESOLUTION
    ) -> Tuple[int, int]:
        """
        计算目标尺寸(保持宽高比)
        
        Args:
            width: 原始宽度
            height: 原始高度
            max_size: 最大尺寸
        
        Returns:
            (target_width, target_height): 目标尺寸
        """
        # 如果已经在范围内,不调整
        if width <= max_size and height <= max_size:
            return width, height
        
        # 计算缩放比例
        scale = min(max_size / width, max_size / height)
        
        # 计算目标尺寸
        target_width = int(width * scale)
        target_height = int(height * scale)
        
        # 确保不小于最小分辨率
        target_width = max(target_width, self.MIN_RESOLUTION)
        target_height = max(target_height, self.MIN_RESOLUTION)
        
        return target_width, target_height
    
    def resize_image(
        self,
        image: np.ndarray,
        target_width: int,
        target_height: int
    ) -> np.ndarray:
        """
        调整图像大小
        
        Args:
            image: 原始图像
            target_width: 目标宽度
            target_height: 目标高度
        
        Returns:
            resized_image: 调整后的图像
        """
        # 使用高质量插值
        resized = cv2.resize(
            image,
            (target_width, target_height),
            interpolation=cv2.INTER_LANCZOS4
        )
        return resized
    
    def compress_image(
        self,
        image: np.ndarray,
        output_path: str,
        max_size: int = MAX_FILE_SIZE,
        quality: int = 95
    ) -> str:
        """
        压缩图像到指定大小
        
        Args:
            image: 图像数组
            output_path: 输出路径
            max_size: 最大文件大小(字节)
            quality: 初始质量(1-100)
        
        Returns:
            output_path: 输出路径
        """
        # 尝试不同的质量级别
        while quality > 10:
            # 保存图像
            cv2.imwrite(
                output_path,
                image,
                [cv2.IMWRITE_JPEG_QUALITY, quality]
            )
            
            # 检查文件大小
            file_size = self.get_file_size(output_path)
            
            if file_size <= max_size:
                print(f"   压缩完成: 质量={quality}, 大小={file_size/1024:.1f}KB")
                return output_path
            
            # 降低质量
            quality -= 5
        
        # 如果还是太大,进一步缩小尺寸
        print(f"   警告: 质量已降至最低,尝试缩小尺寸...")
        height, width = image.shape[:2]
        scale = 0.9
        
        while file_size > max_size and scale > 0.3:
            new_width = int(width * scale)
            new_height = int(height * scale)
            resized = self.resize_image(image, new_width, new_height)
            
            cv2.imwrite(
                output_path,
                resized,
                [cv2.IMWRITE_JPEG_QUALITY, 85]
            )
            
            file_size = self.get_file_size(output_path)
            scale -= 0.1
        
        print(f"   最终大小: {file_size/1024:.1f}KB")
        return output_path
    
    def preprocess_image(
        self,
        input_path: str,
        output_path: Optional[str] = None
    ) -> Tuple[str, dict]:
        """
        预处理图像(完整流程)
        
        Args:
            input_path: 输入图像路径
            output_path: 输出图像路径(可选)
        
        Returns:
            (output_path, info): 输出路径和处理信息
        """
        print(f"\n🔧 图像预处理")
        print(f"   输入: {input_path}")
        
        # 读取图像
        image = cv2.imread(input_path)
        if image is None:
            raise ValueError(f"无法读取图像: {input_path}")
        
        # 获取原始信息
        orig_width, orig_height = self.get_image_resolution(image)
        orig_size = self.get_file_size(input_path)
        
        print(f"   原始分辨率: {orig_width}x{orig_height}")
        print(f"   原始大小: {orig_size/1024:.1f}KB")
        
        info = {
            'original_width': orig_width,
            'original_height': orig_height,
            'original_size': orig_size,
            'resized': False,
            'compressed': False
        }
        
        # 检查是否需要调整分辨率
        need_resize = (
            orig_width > self.MAX_RESOLUTION or
            orig_height > self.MAX_RESOLUTION or
            orig_width < self.MIN_RESOLUTION or
            orig_height < self.MIN_RESOLUTION
        )
        
        if need_resize:
            print(f"   需要调整分辨率...")
            target_width, target_height = self.calculate_target_size(
                orig_width, orig_height
            )
            image = self.resize_image(image, target_width, target_height)
            info['resized'] = True
            info['target_width'] = target_width
            info['target_height'] = target_height
            print(f"   调整后分辨率: {target_width}x{target_height}")
        else:
            info['target_width'] = orig_width
            info['target_height'] = orig_height
            print(f"   分辨率符合要求,无需调整")
        
        # 生成输出路径
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_processed.jpg"
        
        # 检查是否需要压缩
        if orig_size > self.MAX_FILE_SIZE or need_resize:
            print(f"   需要压缩...")
            self.compress_image(image, output_path, self.MAX_FILE_SIZE)
            info['compressed'] = True
        else:
            # 直接保存
            cv2.imwrite(output_path, image, [cv2.IMWRITE_JPEG_QUALITY, 95])
            print(f"   大小符合要求,无需压缩")
        
        # 获取最终信息
        final_size = self.get_file_size(output_path)
        info['final_size'] = final_size
        info['output_path'] = output_path
        
        print(f"   最终大小: {final_size/1024:.1f}KB")
        print(f"   输出: {output_path}")
        print(f"✅ 预处理完成")
        
        return output_path, info
    
    def validate_image(self, file_path: str) -> Tuple[bool, str]:
        """
        验证图像是否符合要求
        
        Args:
            file_path: 图像路径
        
        Returns:
            (valid, message): 是否有效和消息
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False, "文件不存在"
            
            # 读取图像
            image = cv2.imread(file_path)
            if image is None:
                return False, "无法读取图像"
            
            # 检查分辨率
            width, height = self.get_image_resolution(image)
            if width < self.MIN_RESOLUTION or height < self.MIN_RESOLUTION:
                return False, f"分辨率过小: {width}x{height}"
            
            if width > self.MAX_RESOLUTION or height > self.MAX_RESOLUTION:
                return False, f"分辨率过大: {width}x{height}"
            
            # 检查文件大小
            file_size = self.get_file_size(file_path)
            if file_size > self.MAX_FILE_SIZE:
                return False, f"文件过大: {file_size/1024/1024:.1f}MB"
            
            return True, "图像符合要求"
            
        except Exception as e:
            return False, f"验证失败: {e}"


def main():
    """测试函数"""
    print("图像预处理模块测试")
    print("="*60)
    
    preprocessor = ImagePreprocessor()
    
    print("\n配置信息:")
    print(f"  最大文件大小: {preprocessor.MAX_FILE_SIZE/1024/1024}MB")
    print(f"  最小分辨率: {preprocessor.MIN_RESOLUTION}x{preprocessor.MIN_RESOLUTION}")
    print(f"  最大分辨率: {preprocessor.MAX_RESOLUTION}x{preprocessor.MAX_RESOLUTION}")
    
    print("\n使用示例:")
    print("```python")
    print("preprocessor = ImagePreprocessor()")
    print("output_path, info = preprocessor.preprocess_image('input.jpg')")
    print("```")


if __name__ == '__main__':
    main()
