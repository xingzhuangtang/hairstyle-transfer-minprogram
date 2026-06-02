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
from models import db, User, Device
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

    def wechat_login(self, code, device_info=None, nickname=None, avatar_url=None):
        """
        微信登录（支持游客模式、普通用户模式、会员模式）

        用户模式判断逻辑：
        1. 游客模式：user_type='guest'（未绑定微信且未绑定手机号）
        2. 普通用户模式：user_type='registered'（已绑定微信或手机号）
        3. 会员模式：user_type='registered' 且 member_level='vip'

        Args:
            code: 微信登录 code
            device_info: 设备信息（可选）{device_id, device_name, device_type}
            nickname: 微信昵称（可选）
            avatar_url: 微信头像URL（可选）

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
                # 首次微信登录，创建待绑定手机号的账户
                # guest = 有 openid 但未绑定手机号
                # registered = 已绑定手机号
                user = User(
                    openid=openid,
                    unionid=unionid,
                    user_type='guest',  # 未绑定手机号前是 guest
                    member_level="normal",
                    scissor_hairs=0,
                    comb_hairs=0,
                    nickname=nickname,
                    avatar_url=avatar_url,
                    device_id=device_info.get('device_id') if device_info else None,
                )
                db.session.add(user)
                db.session.commit()
                is_new_user = True
                print(f"✅ 新用户注册（微信待绑手机）: openid={openid}, nickname={nickname}, device_id={user.device_id}")

                # 赠送新用户注册福利（1000 根梳子发丝）
                from account_service import AccountService

                account_service = AccountService()
                bonus_result = account_service.register_user(user)
                if bonus_result['success']:
                    print(f"✅ 新用户注册福利已发放：{bonus_result['bonus_hairs']}根梳子发丝")
                else:
                    print(f"⚠️ 新用户注册福利发放失败：{bonus_result.get('error')}")
            else:
                # 老用户登录，更新 unionid（如果之前没有）
                if unionid and not user.unionid:
                    user.unionid = unionid
                # 更新昵称和头像（如果用户还没设置过）
                if nickname and not user.nickname:
                    user.nickname = nickname
                if avatar_url and not user.avatar_url:
                    user.avatar_url = avatar_url
                # 如果老用户还没有 device_id，从当前设备信息补填
                if not user.device_id and device_info and device_info.get('device_id'):
                    user.device_id = device_info['device_id']
                    print(f"✅ 补填老用户 device_id: user_id={user.id}, device_id={user.device_id}")
                db.session.commit()

                # 根据用户类型和会员等级判断模式
                # 游客模式：user_type='guest'
                # 普通用户模式：user_type='registered' 且 member_level='normal'
                # 会员模式：user_type='registered' 且 member_level='vip'

            # 生成 token
            token = self.generate_token(user.id)

            # 自动绑定设备（如果提供了设备信息）
            device_bound = False
            if device_info and device_info.get('device_id'):
                try:
                    device_id = device_info['device_id']
                    device_name = device_info.get('device_name', '未知设备')
                    device_type = device_info.get('device_type', 'unknown')

                    # 检查设备是否已被当前用户绑定
                    existing_device = Device.query.filter_by(user_id=user.id, device_id=device_id).first()
                    if not existing_device:
                        # 检查是否已达到最大设备数
                        device_count = Device.query.filter_by(user_id=user.id).count()
                        if device_count < 2:
                            # 创建新设备记录
                            new_device = Device(
                                user_id=user.id,
                                device_id=device_id,
                                device_name=device_name,
                                device_type=device_type,
                                is_primary=(device_count == 0)
                            )
                            db.session.add(new_device)
                            db.session.commit()
                            device_bound = True
                            print(f"✅ 设备自动绑定成功: user_id={user.id}, device_id={device_id}")
                        else:
                            print(f"⚠️ 用户已达到最大设备数: user_id={user.id}")
                    else:
                        # 更新最后活跃时间
                        existing_device.last_active_at = datetime.now()
                        db.session.commit()
                        device_bound = True
                except Exception as e:
                    print(f"⚠️ 设备绑定失败: {e}")
                    db.session.rollback()

            return {
                "success": True,
                "user_id": user.id,
                "token": token,
                "is_new_user": is_new_user,
                "user_type": user.user_type,  # guest, registered
                "member_level": user.member_level,  # normal, vip
                "user": user.to_dict(),
                "device_bound": device_bound,
                "needs_phone_bind": not user.phone  # 如果用户没有绑定手机号，需要绑定
            }

        except Exception as e:
            print(f"❌ 微信登录失败：{e}")
            return {"success": False, "error": str(e)}

    def phone_login(self, phone, code, device_info=None):
        """
        手机号登录

        Args:
            phone: 手机号
            code: 验证码（兼容'verification_code'参数名）
            device_info: 设备信息（可选）{device_id, device_name, device_type}

        Returns:
            dict: {success, user_id, token, is_new_user}
        """
        try:
            # 兼容两种参数名：'code' 和 'verification_code'
            verification_code = code

            # 开发者账号固定验证码 888888 登录
            from models import User as UserModel
            from config import DEVELOPER_MODE_ENABLED, DEVELOPER_ACCOUNTS

            developer_user = UserModel.query.filter_by(phone=phone).first()
            is_developer_login = (
                DEVELOPER_MODE_ENABLED
                and developer_user is not None
                and developer_user.id in DEVELOPER_ACCOUNTS
            )
            
            if is_developer_login and verification_code == '888888':
                # 开发者账号使用固定验证码登录
                print(f"✅ 开发者账号使用固定验证码登录: phone={phone}, user_id={developer_user.id}")
                user = developer_user
                is_new_user = False
            else:
                # 普通用户需要正常验证码
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
                    # 确保 device_id 不为空：如果前端没传，生成一个
                    final_device_id = device_info.get('device_id') if device_info else None
                    if not final_device_id:
                        final_device_id = str(uuid.uuid4().hex)
                        print(f"⚠️ 前端未传device_id，后端自动生成: {final_device_id}")

                    user = User(
                        phone=phone,
                        member_level="normal",
                        scissor_hairs=0,
                        comb_hairs=0,
                        device_id=final_device_id,
                    )
                    db.session.add(user)
                    db.session.commit()
                    is_new_user = True
                    print(f"✅ 新用户注册（手机号）: phone={phone}, device_id={user.device_id}")

                    # 自动创建设备记录
                    if device_info and final_device_id:
                        try:
                            new_device = Device(
                                user_id=user.id,
                                device_id=final_device_id,
                                device_name=device_info.get('device_name', '未知设备'),
                                device_type=device_info.get('device_type', 'unknown'),
                                is_primary=True
                            )
                            db.session.add(new_device)
                            db.session.commit()
                        except Exception as e:
                            print(f"⚠️ 设备记录创建失败: {e}")
                            db.session.rollback()

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
            # 游客绑定手机号后，更新用户类型为 registered，并赠送注册福利
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

    def bind_phone_with_merge(self, user_id, phone, code):
        """
        绑定手机号（支持账号合并）
        如果手机号已被其他用户绑定，则将当前用户的 openid 合并到该账号

        Args:
            user_id: 当前用户 ID
            phone: 手机号
            code: 验证码

        Returns:
            dict: {success, user, token, merged}
        """
        try:
            from sms_service import SMSService
            sms_service = SMSService()

            if not sms_service.verify_code(phone, code):
                return {"success": False, "error": "验证码错误或已过期"}

            current_user = User.query.get(user_id)
            if not current_user:
                return {"success": False, "error": "用户不存在"}

            # 检查手机号是否已被其他用户绑定
            existing_user = User.query.filter_by(phone=phone).first()
            if existing_user and existing_user.id != user_id:
                # 账号合并：将当前用户的 openid 转移到已有账号
                print(f"🔄 开始账号合并: user_id={user_id} -> target_user_id={existing_user.id}")
                
                if not existing_user.openid and current_user.openid:
                    # 目标账号没有 openid，直接转移
                    existing_user.openid = current_user.openid
                    existing_user.unionid = current_user.unionid
                elif existing_user.openid != current_user.openid:
                    # 两个账号都有 openid，保留目标账号的 openid
                    print(f"⚠️ 两个账号都有openid，保留目标账号的openid")

                # 合并余额
                existing_user.scissor_hairs = (existing_user.scissor_hairs or 0) + (current_user.scissor_hairs or 0)
                existing_user.comb_hairs = (existing_user.comb_hairs or 0) + (current_user.comb_hairs or 0)

                # 合并历史记录（将当前用户的历史记录转移到目标账号）
                from models import ConsumptionRecord, HistoryRecord
                ConsumptionRecord.query.filter_by(user_id=user_id).update({'user_id': existing_user.id})
                HistoryRecord.query.filter_by(user_id=user_id).update({'user_id': existing_user.id})

                # 合并设备绑定
                Device.query.filter_by(user_id=user_id).update({'user_id': existing_user.id})

                # 目标账号绑定手机号并升级为 registered
                existing_user.user_type = 'registered'

                # 取消当前用户的未完成游客续赠记录
                from models import GuestBonusRecord
                GuestBonusRecord.query.filter_by(
                    user_id=user_id,
                    bonus_type='auto_renew',
                    is_completed=False
                ).update({'is_completed': True})

                # 删除当前用户（物理删除）
                db.session.delete(current_user)
                db.session.commit()

                # 生成新 token
                token = self.generate_token(existing_user.id)
                print(f"✅ 账号合并成功: user_id={user_id} -> target_user_id={existing_user.id}")

                return {
                    "success": True,
                    "user": existing_user.to_dict(),
                    "token": token,
                    "merged": True
                }

            # 手机号未被绑定，直接绑定到当前用户
            current_user.phone = phone
            # 只有 guest 用户绑定手机号时才升级为 registered 并取消未完成的游客续赠记录
            if current_user.user_type == 'guest':
                current_user.user_type = 'registered'
                from models import GuestBonusRecord
                GuestBonusRecord.query.filter_by(
                    user_id=user_id,
                    bonus_type='auto_renew',
                    is_completed=False
                ).update({'is_completed': True})
            db.session.commit()

            token = self.generate_token(current_user.id)
            return {
                "success": True,
                "user": current_user.to_dict(),
                "token": token,
                "merged": False
            }

        except Exception as e:
            print(f"❌ 绑定手机号（合并）失败：{e}")
            db.session.rollback()
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
