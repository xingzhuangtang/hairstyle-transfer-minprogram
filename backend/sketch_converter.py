#!/usr/bin/env python3
"""
素描效果转换模块
将图像转换为素描风格
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class SketchConverter:
    """素描效果转换器"""
    
    def __init__(self):
        """初始化转换器"""
        pass
    
    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        转换为灰度图
        
        Args:
            image: 彩色图像
        
        Returns:
            gray: 灰度图像
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        return gray
    
    def dodge(
        self,
        front: np.ndarray,
        back: np.ndarray
    ) -> np.ndarray:
        """
        颜色减淡混合
        
        Args:
            front: 前景图像
            back: 背景图像
        
        Returns:
            result: 混合结果
        """
        # 转换为float32
        front = front.astype(np.float32)
        back = back.astype(np.float32)
        
        # 颜色减淡公式: result = back / (255 - front) * 255
        result = cv2.divide(back, 255.0 - front, scale=256.0)
        
        # 限制范围
        result = np.clip(result, 0, 255)
        result = result.astype(np.uint8)
        
        return result
    
    def pencil_sketch(
        self,
        image: np.ndarray,
        blur_sigma: int = 21
    ) -> np.ndarray:
        """
        铅笔素描效果
        
        Args:
            image: 输入图像
            blur_sigma: 模糊强度(奇数)
        
        Returns:
            sketch: 素描图像
        """
        # 确保blur_sigma是奇数
        if blur_sigma % 2 == 0:
            blur_sigma += 1
        
        # 转换为灰度图
        gray = self.to_grayscale(image)
        
        # 反转图像
        inverted = 255 - gray
        
        # 高斯模糊
        blurred = cv2.GaussianBlur(inverted, (blur_sigma, blur_sigma), 0)
        
        # 颜色减淡混合
        sketch = self.dodge(blurred, gray)
        
        return sketch
    
    def detailed_sketch(
        self,
        image: np.ndarray,
        blur_sigma: int = 15,
        edge_threshold1: int = 50,
        edge_threshold2: int = 150
    ) -> np.ndarray:
        """
        细节素描效果(带边缘检测)
        
        Args:
            image: 输入图像
            blur_sigma: 模糊强度
            edge_threshold1: 边缘检测阈值1
            edge_threshold2: 边缘检测阈值2
        
        Returns:
            sketch: 素描图像
        """
        # 确保blur_sigma是奇数
        if blur_sigma % 2 == 0:
            blur_sigma += 1
        
        # 转换为灰度图
        gray = self.to_grayscale(image)
        
        # 边缘检测
        edges = cv2.Canny(gray, edge_threshold1, edge_threshold2)
        
        # 反转边缘
        edges_inv = 255 - edges
        
        # 基础素描
        base_sketch = self.pencil_sketch(image, blur_sigma)
        
        # 结合边缘
        sketch = cv2.bitwise_and(base_sketch, edges_inv)
        
        return sketch
    
    def artistic_sketch(
        self,
        image: np.ndarray,
        blur_sigma: int = 21,
        sharpen: bool = True
    ) -> np.ndarray:
        """
        艺术素描效果
        
        Args:
            image: 输入图像
            blur_sigma: 模糊强度
            sharpen: 是否锐化
        
        Returns:
            sketch: 素描图像
        """
        # 基础素描
        sketch = self.pencil_sketch(image, blur_sigma)
        
        if sharpen:
            # 锐化处理
            kernel = np.array([
                [-1, -1, -1],
                [-1,  9, -1],
                [-1, -1, -1]
            ])
            sketch = cv2.filter2D(sketch, -1, kernel)
        
        # 对比度增强
        sketch = cv2.convertScaleAbs(sketch, alpha=1.2, beta=10)
        
        return sketch
    
    def color_sketch(
        self,
        image: np.ndarray,
        blur_sigma: int = 21,
        color_intensity: float = 0.3
    ) -> np.ndarray:
        """
        彩色素描效果
        
        Args:
            image: 输入图像
            blur_sigma: 模糊强度
            color_intensity: 颜色强度(0-1)
        
        Returns:
            sketch: 彩色素描图像
        """
        # 基础素描
        gray_sketch = self.pencil_sketch(image, blur_sigma)
        
        # 转换为3通道
        sketch_3ch = cv2.cvtColor(gray_sketch, cv2.COLOR_GRAY2BGR)
        
        # 与原图混合
        if len(image.shape) == 3:
            # 降低原图饱和度
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            hsv[:, :, 1] = hsv[:, :, 1] * color_intensity
            colored = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            
            # 混合
            sketch = cv2.addWeighted(sketch_3ch, 0.7, colored, 0.3, 0)
        else:
            sketch = sketch_3ch
        
        return sketch
    
    def convert(
        self,
        image: np.ndarray,
        style: str = 'pencil',
        **kwargs
    ) -> np.ndarray:
        """
        转换为素描效果(统一接口)
        
        Args:
            image: 输入图像
            style: 素描风格
                - 'pencil': 铅笔素描(默认)
                - 'detailed': 细节素描
                - 'artistic': 艺术素描
                - 'color': 彩色素描
            **kwargs: 其他参数
        
        Returns:
            sketch: 素描图像
        """
        print(f"\n🎨 转换为素描效果")
        print(f"   风格: {style}")
        
        if style == 'pencil':
            sketch = self.pencil_sketch(
                image,
                blur_sigma=kwargs.get('blur_sigma', 21)
            )
        elif style == 'detailed':
            sketch = self.detailed_sketch(
                image,
                blur_sigma=kwargs.get('blur_sigma', 15),
                edge_threshold1=kwargs.get('edge_threshold1', 50),
                edge_threshold2=kwargs.get('edge_threshold2', 150)
            )
        elif style == 'artistic':
            sketch = self.artistic_sketch(
                image,
                blur_sigma=kwargs.get('blur_sigma', 21),
                sharpen=kwargs.get('sharpen', True)
            )
        elif style == 'color':
            sketch = self.color_sketch(
                image,
                blur_sigma=kwargs.get('blur_sigma', 21),
                color_intensity=kwargs.get('color_intensity', 0.3)
            )
        else:
            raise ValueError(f"未知的素描风格: {style}")
        
        print(f"✅ 素描转换完成")
        
        return sketch
    
    def convert_file(
        self,
        input_path: str,
        output_path: str,
        style: str = 'pencil',
        **kwargs
    ) -> str:
        """
        转换图像文件为素描效果
        
        Args:
            input_path: 输入图像路径
            output_path: 输出图像路径
            style: 素描风格
            **kwargs: 其他参数
        
        Returns:
            output_path: 输出路径
        """
        print(f"\n📄 素描转换")
        print(f"   输入: {input_path}")
        print(f"   输出: {output_path}")
        
        # 读取图像
        image = cv2.imread(input_path)
        if image is None:
            raise ValueError(f"无法读取图像: {input_path}")
        
        # 转换
        sketch = self.convert(image, style, **kwargs)
        
        # 保存
        cv2.imwrite(output_path, sketch, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        print(f"✅ 已保存: {output_path}")
        
        return output_path


def main():
    """测试函数"""
    print("素描效果转换模块测试")
    print("="*60)
    
    converter = SketchConverter()
    
    print("\n支持的素描风格:")
    print("  - pencil: 铅笔素描(默认)")
    print("  - detailed: 细节素描")
    print("  - artistic: 艺术素描")
    print("  - color: 彩色素描")
    
    print("\n使用示例:")
    print("```python")
    print("converter = SketchConverter()")
    print("sketch = converter.convert(image, style='pencil')")
    print("converter.convert_file('input.jpg', 'output.jpg', style='artistic')")
    print("```")


if __name__ == '__main__':
    main()
