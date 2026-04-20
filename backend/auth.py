#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户认证模块
支持微信登录、手机号登录、JWT Token
"""

import jwt
import requests
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from models import db, User
from config import get_config


class AuthService:
    """认证服务"""

    def __init__(self):
        self.config = get_config()
        self.jwt_secret_key = self.config.JWT_SECRET_KEY
        self.jwt_access_token_expires = self.config.JWT_ACCESS_TOKEN_EXPIRES

    def generate_token(self, user_id):
        """
        生成 JWT Token

        Args:
            user_id: 用户 ID

        Returns:
            token: JWT Token
        """
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=self.jwt_access_token_expires),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, self.jwt_secret_key, algorithm="HS256")
        return token

    def decode_token(self, token):
        """
        解码 JWT Token

        Args:
            token: JWT Token

        Returns:
            payload: Token payload
        """
        try:
            payload = jwt.decode(token, self.jwt_secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def wechat_login(self, code):
        """
        微信登录（支持游客模式、普通用户模式、会员模式）

        用户模式判断逻辑：
        1. 游客模式：user_type='guest'（未绑定微信且未绑定手机号）
        2. 普通用户模式：user_type='registered'（已绑定微信或手机号）
        3. 会员模式：user_type='registered' 且 member_level='vip'

        Args:
            code: 微信登录 code

        Returns:
            dict: {success, user_id, token, is_new_user, user_type, member_level}
        """
        try:
            # 获取微信 access_token 和 openid
            url = f"https://api.weixin.qq.com/sns/jscode2session"
            params = {
                "appid": self.config.WECHAT_APP_ID,
                "secret": self.config.WECHAT_APP_SECRET,
                "js_code": code,
                "grant_type": "authorization_code",
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "errcode" in data:
                return {"success": False, "error": data["errmsg"]}

            openid = data.get("openid")
            unionid = data.get("unionid")
            session_key = data.get("session_key")

            if not openid:
                return {"success": False, "error": "获取 openid 失败"}

            # 查询或创建用户
            user = User.query.filter_by(openid=openid).first()
            is_new_user = False

            if not user:
                # 首次登录，创建游客账户
                user = User(
                    openid=openid,
                    unionid=unionid,
                    user_type='guest',  # 默认创建游客账户
                    member_level="normal",
                    scissor_hairs=0,
                    comb_hairs=0,
                )
                db.session.add(user)
                db.session.commit()
                is_new_user = True
                print(f"✅ 新用户注册（游客）: openid={openid}")

                # 授予游客首次赠送（198 根梳子发丝）
                from account_service import AccountService

                account_service = AccountService()
                bonus_result = account_service.grant_guest_initial_bonus(user)
                if bonus_result['success']:
                    print(f"✅ 游客首次福利已发放：{bonus_result['hairs']}根梳子发丝")
                else:
                    print(f"⚠️ 游客首次福利发放失败：{bonus_result.get('error')}")
            else:
                # 老用户登录，更新 unionid（如果之前没有）
                if unionid and not user.unionid:
                    user.unionid = unionid
                    db.session.commit()

                # 根据用户类型和会员等级判断模式
                # 游客模式：user_type='guest'
                # 普通用户模式：user_type='registered' 且 member_level='normal'
                # 会员模式：user_type='registered' 且 member_level='vip'

            # 生成 token
            token = self.generate_token(user.id)

            return {
                "success": True,
                "user_id": user.id,
                "token": token,
                "is_new_user": is_new_user,
                "user_type": user.user_type,  # guest, registered
                "member_level": user.member_level,  # normal, vip
                "user": user.to_dict(),
            }

        except Exception as e:
            print(f"❌ 微信登录失败：{e}")
            return {"success": False, "error": str(e)}

    def phone_login(self, phone, code):
        """
        手机号登录

        Args:
            phone: 手机号
            code: 验证码（兼容'verification_code'参数名）

        Returns:
            dict: {success, user_id, token, is_new_user}
        """
        try:
            # 兼容两种参数名：'code' 和 'verification_code'
            verification_code = code

            # 验证验证码
            from sms_service import SMSService

            sms_service = SMSService()

            if not sms_service.verify_code(phone, verification_code):
                return {"success": False, "error": "验证码错误或已过期"}

            # 1. 先按手机号查找
            user = User.query.filter_by(phone=phone).first()
            is_new_user = False

            if not user:
                # 2. 手机号未绑定，检查当前请求是否有 openid 用户（游客模式）
                current_user = self.get_current_user()

                # 3. 如果有 openid 用户且未绑定手机号，直接绑定
                if current_user and current_user.openid and not current_user.phone:
                    user = current_user
                    user.phone = phone
                    # 游客绑定手机号后，更新用户类型为 registered
                    if user.user_type == 'guest':
                        user.user_type = 'registered'
                    db.session.commit()
                    print(f"✅ 游客绑定手机号：user_id={user.id}, openid={user.openid}, phone={phone}, user_type=registered")
                else:
                    # 4. 没有 openid 用户，创建新用户
                    user = User(
                        phone=phone, member_level="normal", scissor_hairs=0, comb_hairs=0
                    )
                    db.session.add(user)
                    db.session.commit()
                    is_new_user = True
                    print(f"✅ 新用户注册（手机号）: phone={phone}")

            else:
                # 手机号已绑定，检查用户状态
                if user.is_deactivated:
                    return {"success": False, "error": "用户账号已被禁用"}

            # 发放新用户福利（1000 根梳子发丝）
            if is_new_user:
                from account_service import AccountService

                account_service = AccountService()
                bonus_result = account_service.register_user(user)

                if bonus_result["success"]:
                    print(
                        f"✅ 新用户福利已发放：{bonus_result['bonus_hairs']}根梳子发丝"
                    )
                else:
                    print(f"⚠️  新用户福利发放失败：{bonus_result.get('error')}")

            # 生成 token
            token = self.generate_token(user.id)

            return {
                "success": True,
                "user_id": user.id,
                "token": token,
                "is_new_user": is_new_user,
                "user": user.to_dict(),
            }

        except Exception as e:
            print(f"❌ 手机号登录失败：{e}")
            return {"success": False, "error": str(e)}

    def bind_phone(self, user_id, phone, code):
        """
        绑定手机号

        Args:
            user_id: 用户 ID
            phone: 手机号
            code: 验证码

        Returns:
            dict: {success, error}
        """
        try:
            # 验证验证码
            from sms_service import SMSService

            sms_service = SMSService()

            if not sms_service.verify_code(phone, code):
                return {"success": False, "error": "验证码错误或已过期"}

            # 检查手机号是否已被绑定
            existing_user = User.query.filter_by(phone=phone).first()
            if existing_user and existing_user.id != user_id:
                return {"success": False, "error": "该手机号已被其他用户绑定"}

            # 绑定手机号
            user = User.query.get(user_id)
            if not user:
                return {"success": False, "error": "用户不存在"}

            user.phone = phone
            # 游客绑定手机号后，更新用户类型为 registered
            if user.user_type == 'guest':
                user.user_type = 'registered'
                # 用户已注册，取消未完成的游客续赠记录
                from models import GuestBonusRecord
                GuestBonusRecord.query.filter_by(
                    user_id=user_id,
                    bonus_type='auto_renew',
                    is_completed=False
                ).update({'is_completed': True})
            db.session.commit()

            return {"success": True, "user": user.to_dict()}

        except Exception as e:
            print(f"❌ 绑定手机号失败：{e}")
            return {"success": False, "error": str(e)}

    def get_current_user(self):
        """
        获取当前登录用户

        Returns:
            User: 当前用户对象
        """
        token = request.headers.get("Authorization")

        if not token:
            return None

        # 移除 Bearer 前缀
        if token.startswith("Bearer "):
            token = token[7:]

        # 解码 token
        payload = self.decode_token(token)
        if not payload:
            return None

        # 获取用户
        user_id = payload.get("user_id")
        user = User.query.get(user_id)

        return user


# 装饰器：需要登录
def login_required(f):
    """登录验证装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_service = AuthService()
        user = auth_service.get_current_user()

        if not user:
            return jsonify({"error": "未登录或登录已过期", "code": 401}), 401

        # 将用户存入 g 对象
        g.current_user = user

        return f(*args, **kwargs)

    return decorated_function


# 装饰器：需要 vip 会员
def vip_required(f):
    """vip 会员验证装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_service = AuthService()
        user = auth_service.get_current_user()

        if not user:
            return jsonify({"error": "未登录或登录已过期", "code": 401}), 401

        if not user.is_vip():
            return jsonify({"error": "此功能仅限 vip 会员使用", "code": 403}), 403

        # 将用户存入 g 对象
        g.current_user = user

        return f(*args, **kwargs)

    return decorated_function


# 装饰器：可选登录
def optional_login(f):
    """可选登录装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_service = AuthService()
        user = auth_service.get_current_user()

        # 将用户存入 g 对象（可能为 None）
        g.current_user = user

        return f(*args, **kwargs)

    return decorated_function

# 开发者模式判断函数
def is_developer_mode_enabled():
    """
    判断开发者模式是否已启用
    从 config.py 读取 DEVELOPER_MODE_ENABLED 配置

    Returns:
        bool: 开发者模式是否启用
    """
    from config import DEVELOPER_MODE_ENABLED
    return DEVELOPER_MODE_ENABLED


def is_developer(user_id=None):
    """
    判断是否为开发者测试账号

    注意：开发者模式必须先通过 DEVELOPER_MODE_ENABLED 启用，
    然后用户 ID 必须在 DEVELOPER_ACCOUNTS 列表中

    Args:
        user_id: 用户 ID，如果不传则从当前请求中获取

    Returns:
        bool: 是否为开发者账号
    """
    from config import DEVELOPER_ACCOUNTS

    # 首先检查开发者模式是否启用
    if not is_developer_mode_enabled():
        return False

    # 如果未配置开发者账号，直接返回 False
    if not DEVELOPER_ACCOUNTS:
        return False

    if user_id is None:
        # 从当前登录用户获取
        auth_service = AuthService()
        user = auth_service.get_current_user()
        if not user:
            return False
        user_id = user.id

    return user_id in DEVELOPER_ACCOUNTS


# 装饰器：开发者权限
def developer_required(f):
    """开发者权限装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_service = AuthService()
        user = auth_service.get_current_user()

        if not user:
            return jsonify({"error": "未登录或登录已过期", "code": 401}), 401

        if not is_developer(user.id):
            return jsonify({"error": "此功能仅限开发者账号使用", "code": 403}), 403

        # 将用户存入 g 对象
        g.current_user = user

        return f(*args, **kwargs)

    return decorated_function
