import json
import base64
import requests
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import os
import time


class BailianImage2ImageHairTransfer:
    def __init__(self, api_key=None, endpoint=None):
        self.api_key = api_key or os.getenv('BAILIAN_API_KEY')
        self.endpoint = endpoint or os.getenv('BAILIAN_ENDPOINT',
                                              'https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis')

        if not self.api_key:
            print("⚠️  警告: 未设置百炼API密钥")
            print("💡 请设置环境变量: export BAILIAN_API_KEY=your_api_key")
        else:
            print(f"✅ 初始化百炼发型迁移服务 (理发师专用)")
            print(f"   API Key: {self.api_key[:10]}...")
            print(f"   Endpoint: {self.endpoint}")

    def image_to_base64(self, image_array):
        """将OpenCV图像转换为base64 (优化为PNG格式)"""
        if image_array is None or image_array.size == 0:
            raise ValueError("无效的图像数据")

        # 确保图像尺寸合规 (384x384 ~ 1024x1024)
        image_array = self._preprocess_image(image_array)

        # 保存为PNG避免压缩失真
        _, buffer = cv2.imencode('.png', image_array)
        base64_data = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/png;base64,{base64_data}"

    def call_image2image_api(self, prompt, src_image_base64, dst_image_base64):
        """调用百炼API (理发师专用优化)"""
        if not self.api_key:
            raise Exception("百炼API密钥未设置")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }

        # 理发师专用请求体 (符合官方API规范)
        request_data = {
            "model": "wan2.5-i2i-preview",
            "input": {
                "prompt": prompt,
                "images": [
                    src_image_base64,  # 发型设计图作为第一张参考图
                    dst_image_base64   # 客户照片作为第二张参考图
                ]
            },
            "parameters": {
                "n": 1,
                "watermark": False  # 不添加水印
            }
        }

        try:
            print("🚀 百炼API调用 (理发师专用模式)")
            print(f"📝 提示词: {prompt}")
            print(f"🖼️  输入图像: 发型设计图 + 客户照片")

            response = requests.post(
                self.endpoint,
                headers=headers,
                json=request_data,
                timeout=120
            )

            if response.status_code == 200:
                result_data = response.json()
                print("✅ API调用成功")

                # 处理异步任务
                if "output" in result_data and "task_id" in result_data["output"]:
                    task_id = result_data["output"]["task_id"]
                    return self._wait_for_async_task(task_id)
                else:
                    print(f"❌ 无效响应: {json.dumps(result_data, indent=2)}")
                    raise Exception("API响应格式错误")

            else:
                error_data = response.json()
                error_code = error_data.get('code', '未知错误')
                error_msg = error_data.get('message', '未知错误信息')
                print(f"❌ API错误 {response.status_code}: {error_code} - {error_msg}")
                print(f"🔧 请求数据: {json.dumps(request_data, indent=2)}")
                raise Exception(f"{error_code}: {error_msg}")

        except Exception as e:
            print(f"❌ API调用失败: {str(e)}")
            raise

    def _wait_for_async_task(self, task_id, max_wait_time=180):
        """等待异步任务完成 (理发师专用优化)"""
        print(f"⏳ 等待发型迁移完成 (任务ID: {task_id})")
        print("💡 专业发型迁移通常需要60-120秒，请耐心等待...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        query_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        start_time = time.time()
        poll_count = 0

        while time.time() - start_time < max_wait_time:
            poll_count += 1
            try:
                print(f"🔍 第{poll_count}次查询任务状态...")
                response = requests.get(query_url, headers=headers, timeout=30)

                if response.status_code == 200:
                    status_data = response.json()
                    task_status = status_data.get("output", {}).get("task_status", "UNKNOWN")

                    print(f"📊 任务状态: {task_status}")

                    if task_status == "SUCCEEDED":
                        print("✅ 任务完成！开始下载生成图像")
                        # 获取结果图像
                        if "output" in status_data and "results" in status_data["output"]:
                            if len(status_data["output"]["results"]) > 0:
                                image_url = status_data["output"]["results"][0]["url"]
                                return self._download_image(image_url)
                            else:
                                raise Exception("任务成功但无结果图像")
                        else:
                            raise Exception("无法找到任务结果")
                    elif task_status == "FAILED":
                        error_msg = status_data.get("output", {}).get("message", "任务失败")
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

    def _download_image(self, image_url):
        """下载生成的图像 (理发师专用优化)"""
        print(f"📥 下载专业发型迁移结果: {image_url}")
        try:
            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                image_array = np.frombuffer(response.content, np.uint8)
                result_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                if result_image is not None:
                    print(f"✅ 图像下载成功，尺寸: {result_image.shape}")
                    return result_image
                else:
                    raise Exception("图像解码失败")
            else:
                raise Exception(f"下载失败: {response.status_code}")

        except Exception as e:
            raise Exception(f"图像下载失败: {str(e)}")

    def transfer_hair(self, src_image, dst_image, strength=0.8):
        """核心功能：发型迁移 (理发师专用优化)"""
        print("💇‍♂️ 开始专业发型迁移 (理发师专用模式)")
        print(f"💪 迁移强度: {strength:.1f} (0.0-1.0)")

        try:
            # 1. 预处理图像 (确保尺寸合规)
            src_image = self._preprocess_image(src_image)
            dst_image = self._preprocess_image(dst_image)

            # 2. 生成专业提示词 (关键优化点)
            prompt = self._generate_hair_prompt()

            # 3. 转换图像为base64
            src_base64 = self.image_to_base64(src_image)
            dst_base64 = self.image_to_base64(dst_image)

            # 4. 调用API
            result_image = self.call_image2image_api(prompt, src_base64, dst_base64)

            # 5. 调整尺寸匹配客户照片
            target_height, target_width = dst_image.shape[:2]
            result_image = cv2.resize(result_image, (target_width, target_height))

            print("✅ 专业发型迁移完成！")
            print("💡 输出结果：客户拥有您设计的发型")
            return result_image

        except Exception as e:
            print(f"❌ 发型迁移失败: {e}")
            print("⚠️ 作为备份，返回原始客户照片")
            return dst_image

    def _generate_hair_prompt(self):
        """生成理发师专用提示词 (关键优化点)"""
        return (
            "将第一张图片的发型迁移到第二张图片的人物上。"
            "关键要求：完全保持第二张图片人物的面部特征、脸型、肤色不变。"
            "不要改变或变形面部。"
            "只替换发型，保留人物其他所有特征。"
            "最终结果应该是：第二张图片的同一个人，但拥有第一张图片的发型。"
            "照片写实风格，自然光照，发型融合无缝，专业品质。"
        )

    def _preprocess_image(self, image):
        """图像预处理 (理发师专用优化)"""
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

    def test_api_connection(self):
        """测试API连接 (理发师专用)"""
        if not self.api_key:
            return False, "API密钥未设置"

        try:
            # 创建专业测试图像
            test_image1 = np.ones((512, 512, 3), dtype=np.uint8) * 255
            cv2.circle(test_image1, (256, 256), 100, (0, 0, 0), -1)  # 发型

            test_image2 = np.ones((512, 512, 3), dtype=np.uint8) * 200
            cv2.rectangle(test_image2, (50, 50), (462, 462), (150, 150, 150), -1)  # 客户面部

            # 测试调用
            result = self.call_image2image_api(
                self._generate_hair_prompt(),
                self.image_to_base64(test_image1),
                self.image_to_base64(test_image2)
            )

            if result is not None:
                return True, "API连接成功 (理发师专用模式)"
            else:
                return False, "API返回空结果"

        except Exception as e:
            return False, f"API连接失败: {str(e)}"


# 工厂函数 (自动检测API配置)
def create_image2image_transfer():
    api_key = os.getenv('BAILIAN_API_KEY')
    endpoint = os.getenv('BAILIAN_ENDPOINT',
                         'https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis')

    if api_key:
        print("🔑 检测到API配置，使用专业发型迁移服务")
        return BailianImage2ImageHairTransfer(api_key, endpoint)
    else:
        print("🔧 未检测到API配置，使用演示模式 (仅用于验证)")
        return _DemoHairTransfer()


class _DemoHairTransfer:
    """演示模式 (仅用于验证流程，不生成真实效果)"""

    def transfer_hair(self, src_image, dst_image, strength=0.8):
        print("🎭 演示模式: 模拟发型迁移效果 (实际使用需设置API密钥)")
        result = dst_image.copy()

        # 添加演示水印
        cv2.putText(result, "DEMO MODE - SET API KEY FOR REAL RESULTS",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(result, f"Strength: {strength:.1f}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        return result