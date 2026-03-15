#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百炼大模型素描转换模块 - 修复版
使用与bailian_image2image相同的REST API调用方式
"""

import os
import base64
import time
import base64
import hashlib
import requests
from http import HTTPStatus
import json


class BailianSketchConverter:
    """百炼素描转换器 - 修复版"""

    def get_deterministic_seed(self, image_path):
        """基于图片内容生成确定性种子，确保相同输入产生相同输出"""
        try:
            with open(image_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            seed = int(file_hash[:8], 16) % 10000
            return seed
        except:
            return 42

    def __init__(self, api_key=None):
        """
        初始化

        Args:
            api_key: 百炼API Key,如果不提供则从环境变量DASHSCOPE_API_KEY读取
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("未找到DASHSCOPE_API_KEY,请设置环境变量或传入api_key参数")

        # 使用与bailian_image2image相同的端点
        self.endpoint = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis"

        # 素描风格prompt模板 - 已重命名
        self.style_prompts = {
            "pencil": "Convert this photo to detailed pencil sketch style, maintain facial features perfectly clear, fine delicate lines with varying thickness, soft realistic shadows and highlights, professional pencil drawing technique with cross-hatching for depth, natural skin texture with subtle shading, expressive eyes with detailed iris and reflections, elaborate hair texture showing individual strands and volume, high contrast black and white pencil drawing, masterful shading techniques creating depth and dimension, pure pencil sketch without any colors",
            "anime": "Japanese anime style with intense vibrant anime color palette, clean precise linework with cel-shading technique, meticulously detailed hair with intensely saturated color strands showing vivid spatial depth, rich anime colors with professional technique, exquisite facial features with typical anime aesthetics and high-contrast skin tones, large expressive eyes with detailed highlights and intensely vibrant iris reflections, elaborate hair texture with vivid intensely colored layers clearly visible, professional anime art style with clean black outlines, intensely vivid multi-color palette with bright high-saturation hues, clear depth perception with overlapping intensely colored hair strands, masterful anime style with spatial hierarchy in vividly colored hair rendering, each hair layer at different depth planes with distinct intense colors creating dramatic color impact, intensely vibrant shading and highlights throughout portrait, highly saturated anime illustration without any color restraint",
            "ink": "Modern fusion Chinese ink wash painting with gentle moderate color saturation, delicate brushwork with contemporary ink strokes in refined hues, elegant hair rendering with visible layered strands showing depth through gentle color variation, each hair layer clearly distinct with harmonious spatial sense between layers, artistic interpretation with modern refined ink strokes, masterful ink wash technique showing hair volume depth and dimensional layers with gentle color enhancement, refined facial features with delicate contemporary ink lines, expressive eyes with precise modern ink detailing, professional Sumi-e fusion style with refined gentle colors, dynamic hair strokes with natural gentle ink coloration from light to moderate, clear spatial relationships between hair strands with refined color layering effect, pronounced layering effect with foreground middle and background hair clearly separated, modern fusion Chinese ink painting with gentle harmonious color tones throughout",
            "color": "Vibrant colored sketch style with 10 to 30 percent COLOR SATURATION, pencil sketch foundation with SUBTLE COLOR ACCENTS, maintaining clear sketch lines with LIGHT PASTEL COLOR TOUCHES, preserving character features with GENTLE COLOR HINTS, artistic beauty with RESTRAINED COLORFUL ELEMENTS, soft color wash over detailed pencil work, MUTED COLOR PALETTE with delicate hues, sketch texture visible through LIGHT COLOR LAYERS, balanced monochrome and SUBTLE COLOR combination",  # 彩色素描
            "vivid": "Vibrant colored sketch style with 10 to 30 percent COLOR SATURATION, pencil sketch foundation with SUBTLE COLOR ACCENTS, maintaining clear sketch lines with LIGHT PASTEL COLOR TOUCHES, preserving character features with GENTLE COLOR HINTS, artistic beauty with RESTRAINED COLORFUL ELEMENTS, soft color wash over detailed pencil work, MUTED COLOR PALETTE with delicate hues, sketch texture visible through LIGHT COLOR LAYERS, balanced monochrome and SUBTLE COLOR combination",  # 兼容别名
        }

        print(f"✅ 初始化百炼素描转换器(修复版)")
        print(f"   API Key: {self.api_key[:10]}...")
        print(f"   Endpoint: {self.endpoint}")

    def image_to_base64(self, image_path):
        """将本地图像文件转换为base64"""
        import cv2
        import numpy as np

        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")

        # 预处理图像（与bailian_image2image保持一致）
        image = self._preprocess_image(image)

        # 转换为PNG Base64
        _, buffer = cv2.imencode(".png", image)
        base64_data = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/png;base64,{base64_data}"

    def _preprocess_image(self, image):
        """图像预处理（与bailian_image2image保持一致）"""
        import cv2
        import numpy as np

        h, w = image.shape[:2]
        min_size = 384
        max_size = 1024

        # 确保图像尺寸在要求范围内
        if min(h, w) < min_size:
            scale = min_size / min(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            print(f"🖼️  图像已放大至: {new_w}x{new_h} (满足API最小尺寸要求)")

        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            print(f"🖼️  图像已缩小至: {new_w}x{new_h} (满足API最大尺寸要求)")

        return image

    def convert(self, image_url, style="ink", watermark=False, local_file_path=None):
        """
        将图像转换为素描风格

        Args:
            image_url: 图像URL(支持公网URL、Base64、本地文件路径)
            style: 素描风格,可选值: pencil, anime, ink, vivid
            watermark: 是否添加水印
            local_file_path: 本地文件路径(用于处理临时URL)

        Returns:
            tuple: (素描图像URL, 处理信息dict)
        """
        print(f"\n🎨 开始百炼素描转换...")
        print(f"   风格: {style}")
        print(f"   输入: {image_url[:100]}...")

        start_time = time.time()

        try:
            prompt = self.style_prompts.get(style, self.style_prompts["ink"])

            # 获取base64图像数据
            if local_file_path and os.path.exists(local_file_path):
                print(f"   使用本地文件转换为Base64: {local_file_path}")
                image_base64 = self.image_to_base64(local_file_path)
                print(f"   Base64转换成功，大小: {len(image_base64)} 字符")
            else:
                # 直接使用URL（暂时不支持）
                raise ValueError("请提供本地文件路径")

            print(f"   📤 调用百炼API...")

            # 使用与bailian_image2image相同的调用方式
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            }

            # 理发师专用请求体 (符合官方API规范)
            request_data = {
                "model": "wan2.5-i2i-preview",
                "input": {
                    "prompt": prompt,
                    "images": [
                        image_base64,  # 单一图像作为参考
                    ],
                },
                "parameters": {"n": 1, "watermark": watermark},
            }

            response = requests.post(
                self.endpoint, headers=headers, json=request_data, timeout=120
            )

            if response.status_code == 200:
                result_data = response.json()
                print("✅ API调用成功")

                # 处理异步任务
                if "output" in result_data and "task_id" in result_data["output"]:
                    task_id = result_data["output"]["task_id"]
                    result_url = self._wait_for_async_task(task_id)

                    elapsed = time.time() - start_time

                    print(f"   ✅ 素描转换成功!")
                    print(f"   耗时: {elapsed:.2f}秒")
                    print(f"   结果URL: {result_url[:100]}...")

                    info = {
                        "success": True,
                        "style": style,
                        "elapsed_time": f"{elapsed:.2f}秒",
                        "result_url": result_url,
                        "task_id": task_id,
                        "prompt": prompt,
                    }

                    return result_url, info
                else:
                    print(f"❌ 无效响应: {json.dumps(result_data, indent=2)}")
                    raise Exception("API响应格式错误")
            else:
                error_data = response.json()
                error_code = error_data.get("code", "未知错误")
                error_msg = error_data.get("message", "未知错误信息")
                print(f"❌ API错误 {response.status_code}: {error_code} - {error_msg}")
                print(f"🔧 请求数据: {json.dumps(request_data, indent=2)}")
                raise Exception(f"{error_code}: {error_msg}")

        except Exception as e:
            error_msg = f"素描转换异常: {str(e)}"
            print(f"   ❌ {error_msg}")
            return None, {"success": False, "error": error_msg}

    def _wait_for_async_task(self, task_id, max_wait_time=600):
        """等待异步任务完成（10分钟超时）"""
        print(f"⏳ 等待素描转换完成 (任务ID: {task_id})")
        print("💡 素描转换通常需要60-120秒，请耐心等待...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        query_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        start_time = time.time()
        poll_count = 0

        while time.time() - start_time < max_wait_time:
            poll_count += 1
            try:
                print(f"🔍 第{poll_count}次查询任务状态...")
                response = requests.get(query_url, headers=headers, timeout=120)

                if response.status_code == 200:
                    status_data = response.json()
                    task_status = status_data.get("output", {}).get(
                        "task_status", "UNKNOWN"
                    )

                    print(f"📊 任务状态: {task_status}")

                    if task_status == "SUCCEEDED":
                        print("✅ 任务完成！开始下载生成图像")
                        # 获取结果图像
                        if (
                            "output" in status_data
                            and "results" in status_data["output"]
                        ):
                            if len(status_data["output"]["results"]) > 0:
                                image_url = status_data["output"]["results"][0]["url"]

                                # 验证 URL 是否有效
                                if not image_url or not image_url.startswith(
                                    ("http://", "https://")
                                ):
                                    raise Exception(f"无效的图片URL: {image_url}")

                                # 验证图片 URL 是否可访问（快速 HEAD 请求）- 可选检查
                                try:
                                    head_response = requests.head(
                                        image_url, timeout=10, allow_redirects=True
                                    )
                                    if head_response.status_code != 200:
                                        print(
                                            f"   ⚠️ HEAD请求返回 {head_response.status_code}，但将继续尝试下载"
                                        )
                                    else:
                                        # 检查 Content-Type
                                        content_type = head_response.headers.get(
                                            "Content-Type", ""
                                        )
                                        if "image" not in content_type.lower():
                                            print(
                                                f"   ⚠️ Content-Type不是图片 ({content_type})，但将继续尝试下载"
                                            )
                                        else:
                                            print(
                                                f"   图片URL验证通过: {image_url[:80]}..."
                                            )
                                except Exception as url_check_error:
                                    print(f"   ⚠️ HEAD请求验证失败: {url_check_error}")
                                    print(
                                        f"   继续使用URL（来自Dashscope API）: {image_url[:80]}..."
                                    )

                                return image_url
                            else:
                                raise Exception("任务成功但无结果图像")
                        else:
                            raise Exception("无法找到任务结果")
                    elif task_status == "FAILED":
                        error_msg = status_data.get("output", {}).get(
                            "message", "任务失败"
                        )
                        raise Exception(f"异步任务失败: {error_msg}")
                    else:
                        print("⏳ 任务处理中，等待10秒后继续查询...")
                        time.sleep(10)
                else:
                    print(f"❌ 查询失败: {response.status_code}")
                    time.sleep(10)

            except Exception as e:
                print(f"❌ 查询错误: {e}")
                time.sleep(10)

        raise Exception(f"任务等待超时 (超过 {max_wait_time} 秒)")

    def download_result(self, result_url, save_path):
        """
        下载素描结果图像

        Args:
            result_url: 结果图像URL
            save_path: 保存路径

        Returns:
            bool: 是否成功
        """
        try:
            print(f"\n📥 下载素描结果...")
            print(f"   URL: {result_url[:100]}...")
            print(f"   保存到: {save_path}")

            response = requests.get(result_url, timeout=120)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                f.write(response.content)

            print(f"   ✅ 下载成功!")
            return True

        except Exception as e:
            print(f"   ❌ 下载失败: {e}")
            return False


def test_converter():
    """测试素描转换器"""
    print("=" * 60)
    print("百炼素描转换器测试(修复版)")
    print("=" * 60)

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 未设置DASHSCOPE_API_KEY环境变量")
        return

    print(f"✅ API Key已设置: {api_key[:20]}...")

    try:
        converter = BailianSketchConverter(api_key)
        print("✅ 素描转换器创建成功")
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        return


if __name__ == "__main__":
    test_converter()
