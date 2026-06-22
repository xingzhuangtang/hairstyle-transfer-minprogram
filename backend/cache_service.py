#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存服务模块
封装 Redis 连接和常用操作，支持 JSON 序列化/反序列化
Redis 不可用时自动降级（返回 None）
"""

import json
import redis
from config import get_config


class CacheService:
    """Redis 缓存服务"""

    def __init__(self):
        self.config = get_config()
        self.redis_client = None

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
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            else:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            # 测试连接
            self.redis_client.ping()
            print(f"✅ CacheService Redis 连接成功 - {redis_host}:{redis_port}")
        except Exception as e:
            print(f"⚠️ CacheService Redis 连接失败，缓存功能降级: {e}")
            self.redis_client = None

    def get(self, key):
        """
        获取缓存数据（自动 JSON 反序列化）

        Args:
            key: 缓存键

        Returns:
            反序列化后的数据，缓存不可用或不存在时返回 None
        """
        if not self.redis_client:
            return None
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            print(f"⚠️ CacheService get 失败: key={key}, error={e}")
            return None

    def set(self, key, value, expire_seconds=None):
        """
        设置缓存数据（自动 JSON 序列化）

        Args:
            key: 缓存键
            value: 缓存值（必须是 JSON 可序列化的）
            expire_seconds: 过期时间（秒），None 表示不过期

        Returns:
            bool: 是否成功
        """
        if not self.redis_client:
            return False
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            if expire_seconds:
                self.redis_client.setex(key, expire_seconds, serialized)
            else:
                self.redis_client.set(key, serialized)
            return True
        except Exception as e:
            print(f"⚠️ CacheService set 失败: key={key}, error={e}")
            return False

    def delete(self, key):
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            bool: 是否成功
        """
        if not self.redis_client:
            return False
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"⚠️ CacheService delete 失败: key={key}, error={e}")
            return False

    def exists(self, key):
        """
        检查缓存键是否存在

        Args:
            key: 缓存键

        Returns:
            bool: 是否存在
        """
        if not self.redis_client:
            return False
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"⚠️ CacheService exists 失败: key={key}, error={e}")
            return False


# 全局单例
_cache_service_instance = None


def get_cache_service():
    """获取缓存服务单例"""
    global _cache_service_instance
    if _cache_service_instance is None:
        _cache_service_instance = CacheService()
    return _cache_service_instance
