#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
空白图像检测守卫 - 防止阿里云 API 返回空白/白板结果时扣款
所有图像下载和返回路径都必须经过此模块校验
"""

import numpy as np
import cv2
import os
import logging

logger = logging.getLogger(__name__)


def is_blank_image(image, brightness_threshold=240, std_threshold=15, non_white_ratio_threshold=0.02):
    """
    检测图像是否为空白/白板图像

    三重检测机制:
    1. 平均亮度 > brightness_threshold (整体偏白)
    2. 标准差 < std_threshold (几乎没有内容变化)
    3. 非白色像素占比 < non_white_ratio_threshold (几乎全是白色)

    Args:
        image: numpy array (OpenCV 格式)
        brightness_threshold: 平均亮度阈值 (0-255), 高于此值认为偏白
        std_threshold: 标准差阈值, 低于此值认为没有内容
        non_white_ratio_threshold: 非白色像素占比阈值

    Returns:
        tuple: (is_blank: bool, reason: str, stats: dict)
    """
    if image is None:
        return True, "图像为空(None)", {"error": "None image"}

    if image.size == 0:
        return True, "图像数据为空", {"error": "empty array"}

    h, w = image.shape[:2]
    total_pixels = h * w

    if total_pixels < 100:
        return True, f"图像尺寸过小: {w}x{h}", {"width": w, "height": h}

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    mean_brightness = float(np.mean(gray))
    std_brightness = float(np.std(gray))

    non_white_mask = gray < 240
    non_white_ratio = float(np.sum(non_white_mask)) / total_pixels

    stats = {
        "width": w,
        "height": h,
        "mean_brightness": round(mean_brightness, 2),
        "std_brightness": round(std_brightness, 2),
        "non_white_ratio": round(non_white_ratio, 6),
    }

    reasons = []

    if mean_brightness > brightness_threshold and std_brightness < std_threshold:
        reasons.append(f"高亮度低方差(亮度={mean_brightness:.1f}, 方差={std_brightness:.1f})")

    if non_white_ratio < non_white_ratio_threshold:
        reasons.append(f"非白像素占比极低({non_white_ratio:.4f} < {non_white_ratio_threshold})")

    if std_brightness < 3.0:
        reasons.append(f"标准差极低({std_brightness:.1f} < 3.0), 图像几乎纯色")

    if reasons:
        return True, "; ".join(reasons), stats

    return False, "图像内容正常", stats


def check_image_file(file_path, brightness_threshold=240, std_threshold=15, non_white_ratio_threshold=0.02):
    """
    检测图像文件是否为空白

    Args:
        file_path: 图像文件路径

    Returns:
        tuple: (is_blank: bool, reason: str, stats: dict)
    """
    if not os.path.exists(file_path):
        return True, f"文件不存在: {file_path}", {"error": "file_not_found"}

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return True, f"文件大小为0: {file_path}", {"error": "empty_file"}

    image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    if image is None:
        return True, f"图像解码失败: {file_path}", {"error": "decode_failed"}

    return is_blank_image(image, brightness_threshold, std_threshold, non_white_ratio_threshold)


def validate_result_image(image_or_path, operation_name="unknown", auto_retry_func=None, max_retries=2):
    """
    验证结果图像是否有效，如果无效且提供了重试函数则自动重试

    Args:
        image_or_path: numpy array 或文件路径
        operation_name: 操作名称(用于日志)
        auto_retry_func: 可选的重试函数，返回新的 image_or_path
        max_retries: 最大重试次数

    Returns:
        tuple: (is_valid: bool, image, reason: str, stats: dict)
            如果验证通过: (True, image, "正常", stats)
            如果验证失败: (False, None, reason, stats)
    """
    current = image_or_path
    last_reason = ""
    last_stats = {}

    for attempt in range(max_retries + 1):
        if isinstance(current, str):
            is_blank, reason, stats = check_image_file(current)
        else:
            is_blank, reason, stats = is_blank_image(current)

        if not is_blank:
            if attempt > 0:
                logger.info(f"[{operation_name}] 第{attempt}次重试后获得有效图像")
            return True, current, "正常", stats

        last_reason = reason
        last_stats = stats
        logger.warning(f"[{operation_name}] 检测到空白图像 (尝试 {attempt + 1}/{max_retries + 1}): {reason}")

        if attempt < max_retries and auto_retry_func is not None:
            try:
                current = auto_retry_func()
                if current is None:
                    break
            except Exception as e:
                logger.error(f"[{operation_name}] 重试失败: {e}")
                break
        else:
            break

    logger.error(f"[{operation_name}] 最终结果仍为空白: {last_reason}")
    return False, None, last_reason, last_stats
