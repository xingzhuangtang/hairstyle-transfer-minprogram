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
        生成JWT Token

        Args:
            user_id: 用户ID

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
        解码JWT Token

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
        微信登录

        Args:
            code: 微信登录code

        Returns:
            dict: {success, user_id, token, is_new_user}
        """
        try:
            # 获取微信access_token和openid
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
                return {"success": False, "error": "获取openid失败"}

            # 查询或创建用户
            user = User.query.filter_by(openid=openid).first()
            is_new_user = False

            if not user:
                # 创建新用户
                user = User(
                    openid=openid,
                    unionid=unionid,
                    member_level="normal",
                    scissor_hairs=0,
                    comb_hairs=0,
                )
                db.session.add(user)
                db.session.commit()
                is_new_user = True
                print(f"✅ 新用户注册: openid={openid}")

                # 赠送新用户福利（1000根梳子发丝）
                from account_service import AccountService

                account_service = AccountService()
                bonus_result = account_service.register_user(user)
                if bonus_result["success"]:
                    print(
                        f"✅ 新用户福利已发放: {bonus_result['bonus_hairs']}根梳子发丝"
                    )
                else:
                    print(f"⚠️ 新用户福利发放失败: {bonus_result.get('error')}")
            else:
                # 更新unionid（如果之前没有）
                if unionid and not user.unionid:
                    user.unionid = unionid
                    db.session.commit()

            # 生成token
            token = self.generate_token(user.id)

            return {
                "success": True,
                "user_id": user.id,
                "token": token,
                "is_new_user": is_new_user,
                "user": user.to_dict(),
            }

        except Exception as e:
            print(f"❌ 微信登录失败: {e}")
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

            # 查询或创建用户
            user = User.query.filter_by(phone=phone).first()
            is_new_user = False

            if not user:
                # 创建新用户
                user = User(
                    phone=phone, member_level="normal", scissor_hairs=0, comb_hairs=0
                )
                db.session.add(user)
                db.session.commit()
                is_new_user = True

            else:
                # 检查用户状态
                if user.is_deactivated:
                    return {"success": False, "error": "用户账号已被禁用"}

            # 发放新用户福利（1000根梳子发丝）
            if is_new_user:
                from account_service import AccountService

                account_service = AccountService()
                bonus_result = account_service.register_user(user)

                if bonus_result["success"]:
                    print(
                        f"✅ 新用户福利已发放: {bonus_result['bonus_hairs']}根梳子发丝"
                    )
                else:
                    print(f"⚠️  新用户福利发放失败: {bonus_result.get('error')}")

            # 生成token
            token = self.generate_token(user.id)

            return {
                "success": True,
                "user_id": user.id,
                "token": token,
                "is_new_user": is_new_user,
                "user": user.to_dict(),
            }

        except Exception as e:
            print(f"❌ 手机号登录失败: {e}")
            return {"success": False, "error": str(e)}

    def bind_phone(self, user_id, phone, code):
        """
        绑定手机号

        Args:
            user_id: 用户ID
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
            db.session.commit()

            return {"success": True, "user": user.to_dict()}

        except Exception as e:
            print(f"❌ 绑定手机号失败: {e}")
            return {"success": False, "error": str(e)}

    def get_current_user(self):
        """
        获取当前登录用户

        Returns:
            User: 当前用户对象
        """
        token = request.headers.get("Authorization")
        print(f"[DEBUG] Authorization header: {token}")

        if not token:
            print("[DEBUG] No Authorization header found")
            return None

        # 移除Bearer前缀
        if token.startswith("Bearer "):
            token = token[7:]
        print(f"[DEBUG] Token after Bearer removal: {token[:50]}...")

        # 解码token
        payload = self.decode_token(token)
        if not payload:
            print(f"[DEBUG] Token decode failed")
            return None

        print(f"[DEBUG] Token decoded successfully: {payload}")

        # 获取用户
        user_id = payload.get("user_id")
        user = User.query.get(user_id)

        print(f"[DEBUG] User found: {user}")

        return user


# 装饰器：需要登录
def login_required(f):
    """登录验证装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("[LOGIN_DECORATOR] Checking authentication...")
        auth_service = AuthService()
        user = auth_service.get_current_user()
        print(f"[LOGIN_DECORATOR] User: {user}")

        if not user:
            print("[LOGIN_DECORATOR] Authentication failed!")
            return jsonify({"error": "未登录或登录已过期", "code": 401}), 401

        # 将用户存入g对象
        g.current_user = user

        return f(*args, **kwargs)

    return decorated_function


# 装饰器：需要vip 会员
def vip_required(f):
    """vip 会员验证装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_service = AuthService()
        user = auth_service.get_current_user()

        if not user:
            return jsonify({"error": "未登录或登录已过期", "code": 401}), 401

        if not user.is_vip():
            return jsonify({"error": "此功能仅限vip 会员使用", "code": 403}), 403

        # 将用户存入g对象
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

        # 将用户存入g对象（可能为None）
        g.current_user = user

        return f(*args, **kwargs)

    return decorated_function
