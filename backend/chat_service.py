#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时聊天业务服务
"""

import hmac
import hashlib
import re
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from models import db, ChatMessage, User
from chat_notifier import ChatNotifier


# 简单的内存限流器（5条/分钟滑动窗口）
_send_limits = {}

def check_send_limit(user_id):
    """检查用户发消息频率，返回是否允许发送"""
    now = time.time()
    window = 60  # 60秒窗口
    max_messages = 5  # 最多5条

    if user_id not in _send_limits:
        _send_limits[user_id] = []

    # 清理过期记录
    _send_limits[user_id] = [t for t in _send_limits[user_id] if now - t < window]

    if len(_send_limits[user_id]) >= max_messages:
        return False

    _send_limits[user_id].append(now)
    return True


def generate_reply_token(user_id):
    """
    生成管理员回复链接的 HMAC-SHA256 签名 token
    24小时过期
    """
    from config import get_config
    config = get_config()
    secret = config.SECRET_KEY or 'default-secret-key'

    payload = f"{user_id}:{int(time.time()) + 86400}"  # 24小时后过期
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    token = f"{payload}:{signature}"
    return token


def verify_reply_token(token):
    """
    验证管理员回复链接的 HMAC 签名 token
    返回 (identifier, identifier_type) 或 (None, None)
    identifier_type 为 'user_id' 或 'phone'
    """
    from config import get_config
    config = get_config()
    secret = config.SECRET_KEY or 'default-secret-key'

    try:
        parts = token.split(':')
        if len(parts) != 3:
            return None, None

        identifier_str, expire_str, signature = parts
        expire_time = int(expire_str)

        # 检查过期
        if time.time() > expire_time:
            return None, None

        # 验证签名
        payload = f"{identifier_str}:{expire_str}"
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return None, None

        # 判断是 user_id 还是 phone
        try:
            user_id = int(identifier_str)
            # 检查是否真的是 user_id（数据库中是否存在）
            user = User.query.get(user_id)
            if user:
                return user_id, 'user_id'
        except (ValueError, TypeError):
            pass

        # 当作手机号处理
        return identifier_str, 'phone'

    except (ValueError, TypeError):
        return None, None


def sanitize_content(content):
    """清洗消息内容，移除HTML标签"""
    if not content:
        return ''
    # 用正则移除所有HTML标签
    cleaned = re.sub(r'<[^>]+>', '', content)
    # 截断到 2000 字符
    return cleaned[:2000].strip()


class ChatService:
    """聊天服务"""

    @staticmethod
    def send_message(user_id, content):
        """
        用户发送消息

        Returns:
            (success, message, chat_message)
        """
        # 限流检查
        if not check_send_limit(user_id):
            return False, '发送过于频繁，请稍后再试', None

        # 内容清洗
        content = sanitize_content(content)
        if not content:
            return False, '消息内容不能为空', None

        # 保存消息
        chat_message = ChatMessage(
            user_id=user_id,
            sender_type='user',
            content=content
        )
        db.session.add(chat_message)
        db.session.commit()

        # 发送企业微信通知
        try:
            user = User.query.get(user_id)
            if user:
                reply_token = generate_reply_token(user_id)
                notifier = ChatNotifier()
                notifier.send_new_message_notification(user, content, reply_token)
        except Exception as e:
            print(f"发送企业微信通知失败: {e}")

        return True, '发送成功', chat_message

    @staticmethod
    def get_messages(user_id, since=None, limit=50):
        """
        获取用户聊天记录（增量轮询）

        Args:
            user_id: 用户ID
            since: ISO格式时间字符串，只返回此时间之后的消息
            limit: 返回消息数量限制

        Returns:
            list of ChatMessage
        """
        query = ChatMessage.query.filter_by(user_id=user_id)

        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                query = query.filter(ChatMessage.created_at > since_dt)
            except (ValueError, AttributeError):
                pass

        messages = query.order_by(ChatMessage.created_at.asc()).limit(limit).all()

        # 注意：不在这里标记已读，由 /chat/mark-read 接口统一处理
        return messages

    @staticmethod
    def get_unread_count(user_id):
        """
        获取未读通知数量
        包含两部分：
        1. 聊天系统中 admin 回复的未读消息
        2. 客户留言中已被标记为 processing（管理员已查看/处理）但用户还未读的消息
        """
        # admin 聊天消息未读数
        chat_unread = ChatMessage.query.filter_by(
            user_id=user_id,
            sender_type='admin',
            is_read=False
        ).count()

        # 留言已处理但未通知用户的数量（processing 状态代表管理员已介入）
        from models import Message
        msg_unread = Message.query.filter_by(
            user_id=user_id,
            status='processing'
        ).count()

        return chat_unread + msg_unread

    @staticmethod
    def reply_message(user_id, content, admin_id=None):
        """
        管理员回复消息

        Args:
            user_id: 用户ID
            content: 回复内容
            admin_id: 管理员ID（可选）

        Returns:
            (success, message, chat_message)
        """
        # 验证用户存在
        user = User.query.get(user_id)
        if not user:
            return False, '用户不存在', None

        # 内容清洗
        content = sanitize_content(content)
        if not content:
            return False, '回复内容不能为空', None

        # 保存回复
        chat_message = ChatMessage(
            user_id=user_id,
            sender_type='admin',
            content=content
        )
        db.session.add(chat_message)
        db.session.commit()

        return True, '回复成功', chat_message
