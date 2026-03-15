#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短信服务模块
使用阿里云短信服务发送验证码
"""

import random
import time
from datetime import datetime, timedelta
from alibabacloud_dysmsapi20170525.client import Client as DysmsClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysms_models
from config import get_config


class SMSService:
    """短信服务"""

    def __init__(self):
        self.config = get_config()
        self.access_key_id = self.config.SMS_ACCESS_KEY_ID
        self.access_key_secret = self.config.SMS_ACCESS_KEY_SECRET
        self.sign_name = self.config.SMS_SIGN_NAME
        self.template_code = self.config.SMS_TEMPLATE_CODE

        # 验证码有效期（分钟）
        self.code_expire_minutes = 5

        # 验证码缓存（开发环境也使用Redis）
        import redis

        try:
            redis_host = (
                self.config.REDIS_HOST
                if hasattr(self.config, "REDIS_HOST")
                else "localhost"
            )
            redis_port = (
                self.config.REDIS_PORT if hasattr(self.config, "REDIS_PORT") else 6379
            )
            redis_password = (
                self.config.REDIS_PASSWORD
                if hasattr(self.config, "REDIS_PASSWORD")
                else ""
            )
            redis_db = self.config.REDIS_DB if hasattr(self.config, "REDIS_DB") else 0

            if redis_password:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    db=redis_db,
                    decode_responses=True,
                )
            else:
                self.redis_client = redis.Redis(
                    host=redis_host, port=redis_port, db=redis_db, decode_responses=True
                )
            print(f"✅ SMS服务使用Redis存储验证码 - {redis_host}:{redis_port}")
        except Exception as e:
            print(f"⚠️ Redis连接失败，使用内存缓存: {e}")
            self.redis_client = None

        # 初始化内存缓存（备用）
        self.code_cache = {}

    def _create_client(self):
        """创建阿里云短信客户端"""
        config = open_api_models.Config(
            access_key_id=self.access_key_id, access_key_secret=self.access_key_secret
        )
        config.endpoint = "dysmsapi.aliyuncs.com"
        return DysmsClient(config)

    def generate_code(self):
        """生成6位验证码"""
        return str(random.randint(100000, 999999))

    def send_code(self, phone):
        """
        发送短信验证码

        Args:
            phone: 手机号

        Returns:
            dict: {success, error, expire_time}
        """
        try:
            # 检查发送频率（1分钟内只能发送1次）
            cache_key = f"sms:{phone}"
            if cache_key in self.code_cache:
                last_send_time = self.code_cache[cache_key]["send_time"]
                if time.time() - last_send_time < 60:
                    return {"success": False, "error": "发送过于频繁，请稍后再试"}

            # 生成验证码
            code = self.generate_code()

            # 开发环境测试模式：如果未配置短信，直接在日志显示验证码
            if (
                not self.access_key_id
                or not self.access_key_secret
                or self.access_key_id == "your-access-key-id"
            ):
                # 测试模式：不发送短信，直接缓存验证码到Redis
                expire_time = datetime.now() + timedelta(
                    minutes=self.code_expire_minutes
                )

                # 使用Redis存储
                if self.redis_client:
                    expire_seconds = int(self.code_expire_minutes * 60)
                    self.redis_client.hset(
                        cache_key,
                        mapping={
                            "code": code,
                            "send_time": str(time.time()),
                            "expire_time": expire_time.isoformat(),
                        },
                    )
                    self.redis_client.expire(cache_key, expire_seconds)
                    print(f"✅ Redis存储验证码成功: phone={phone}, code={code}")
                else:
                    # 备用内存缓存
                    self.code_cache[cache_key] = {
                        "code": code,
                        "send_time": time.time(),
                        "expire_time": expire_time,
                    }
                    print(f"✅ 内存存储验证码成功: phone={phone}, code={code}")

                print(f"\n{'=' * 60}")
                print(f"🧪 开发环境测试模式")
                print(f"📱 手机号: {phone}")
                print(f"🔐 验证码: {code}")
                print(f"⏰ 有效期: {self.code_expire_minutes}分钟")
                print(f"{'=' * 60}\n")

                return {
                    "success": True,
                    "expire_time": expire_time.isoformat(),
                    "test_mode": True,
                    "code": code,  # 测试模式返回验证码
                }

            # 生产环境：发送真实短信
            client = self._create_client()

            send_sms_request = dysms_models.SendSmsRequest(
                sign_name=self.sign_name,
                template_code=self.template_code,
                phone_numbers=phone,
                template_param=f'{{"code":"{code}"}}',
            )

            runtime = open_api_models.RuntimeOptions()
            response = client.send_sms_with_options(send_sms_request, runtime)

            if response.body.code == "OK":
                # 缓存验证码
                expire_time = datetime.now() + timedelta(
                    minutes=self.code_expire_minutes
                )
                self.code_cache[cache_key] = {
                    "code": code,
                    "send_time": time.time(),
                    "expire_time": expire_time,
                }

                print(f"✅ 短信发送成功: phone={phone}, code={code}")

                return {"success": True, "expire_time": expire_time.isoformat()}
            else:
                print(
                    f"❌ 短信发送失败: {response.body.code} - {response.body.message}"
                )
                return {"success": False, "error": response.body.message}

        except Exception as e:
            print(f"❌ 短信发送异常: {e}")
            return {"success": False, "error": str(e)}

    def verify_code(self, phone, code):
        """
        验证验证码

        Args:
            phone: 手机号
            code: 验证码

        Returns:
            bool: 验证是否成功
        """
        try:
            cache_key = f"sms:{phone}"

            # 首先尝试从Redis获取
            if self.redis_client:
                cached_data = self.redis_client.hgetall(cache_key)

                if not cached_data:
                    print(f"❌ Redis验证码不存在: phone={phone}")
                    return False

                # 检查验证码是否正确
                cached_code = cached_data.get("code", "")
                if cached_code != code:
                    print(
                        f"❌ 验证码错误: phone={phone}, input={code}, cached={cached_code}"
                    )
                    return False

                # 检查验证码是否过期
                expire_time_str = cached_data.get("expire_time", "")
                if expire_time_str:
                    expire_time = datetime.fromisoformat(expire_time_str)
                    if datetime.now() > expire_time:
                        print(f"❌ 验证码已过期: phone={phone}")
                        self.redis_client.delete(cache_key)
                        return False

                # 验证成功，删除验证码（一次性使用）
                self.redis_client.delete(cache_key)
                print(f"✅ Redis验证码验证成功: phone={phone}")
                return True

            # 备用：内存缓存验证
            if cache_key not in self.code_cache:
                print(f"❌ 内存验证码不存在: phone={phone}")
                return False

            cached_data = self.code_cache[cache_key]

            # 检查验证码是否正确
            if cached_data["code"] != code:
                print(
                    f"❌ 验证码错误: phone={phone}, input={code}, cached={cached_data['code']}"
                )
                return False

            # 检查验证码是否过期
            if datetime.now() > cached_data["expire_time"]:
                print(f"❌ 验证码已过期: phone={phone}")
                # 删除过期验证码
                del self.code_cache[cache_key]
                return False

            # 验证成功，删除验证码（一次性使用）
            del self.code_cache[cache_key]
            print(f"✅ 内存验证码验证成功: phone={phone}")
            return True

        except Exception as e:
            print(f"❌ 验证码验证异常: {e}")
            return False

    def clean_expired_codes(self):
        """清理过期验证码"""
        try:
            current_time = datetime.now()
            expired_keys = []

            for key, data in self.code_cache.items():
                if current_time > data["expire_time"]:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.code_cache[key]

            if expired_keys:
                print(f"✅ 清理过期验证码: {len(expired_keys)}条")

        except Exception as e:
            print(f"❌ 清理过期验证码异常: {e}")


# 测试代码
if __name__ == "__main__":
    sms_service = SMSService()

    # 发送验证码
    phone = input("请输入手机号: ")
    result = sms_service.send_code(phone)

    if result["success"]:
        print(f"✅ 验证码发送成功，有效期: {result['expire_time']}")

        # 验证验证码
        code = input("请输入验证码: ")
        if sms_service.verify_code(phone, code):
            print("✅ 验证码验证成功")
        else:
            print("❌ 验证码验证失败")
    else:
        print(f"❌ 验证码发送失败: {result['error']}")
