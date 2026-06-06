#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型 + 认证服务
使用SQLAlchemy ORM
"""

import jwt
import requests
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index
from config import get_config


db = SQLAlchemy()


# ==================== 数据库模型 ====================

class User(db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    openid = db.Column(db.String(128), unique=True, nullable=True, comment='微信openid')
    unionid = db.Column(db.String(128), unique=True, nullable=True, comment='微信unionid')
    phone = db.Column(db.String(20), unique=True, nullable=True, comment='手机号')
    device_id = db.Column(db.String(64), nullable=True, comment='主设备追踪ID（永不改变）')
    nickname = db.Column(db.String(100), nullable=True, comment='昵称')
    avatar_url = db.Column(db.String(500), nullable=True, comment='头像URL')
    member_level = db.Column(db.Enum('normal', 'vip'), default='normal', comment='会员等级')
    member_expire_at = db.Column(db.DateTime, nullable=True, comment='会员到期时间')
    scissor_hairs = db.Column(db.Integer, default=0, comment='剪刀卡槽头发丝数量')
    comb_hairs = db.Column(db.Integer, default=0, comment='梳子卡槽头发丝数量')
    total_recharge = db.Column(db.Numeric(10, 2), default=0.00, comment='累计充值金额')
    total_consumed_hairs = db.Column(db.Integer, default=0, comment='累计消耗头发丝')
    user_type = db.Column(db.Enum('guest', 'registered'), default='registered', comment='用户类型')
    is_deactivated = db.Column(db.Boolean, default=False, comment='是否已注销')
    deactivated_at = db.Column(db.DateTime, nullable=True, comment='注销时间')
    # 推广返佣相关字段
    cash_balance = db.Column(db.Numeric(10, 2), default=0.00, comment='存钱罐余额(元)')
    total_referral_earnings = db.Column(db.Numeric(10, 2), default=0.00, comment='累计推广收益(元)')
    referral_code = db.Column(db.String(32), nullable=True, comment='用户专属推广码')
    referral_count = db.Column(db.Integer, default=0, comment='成功推广人数')
    # 访客模式赠送追踪
    guest_bonus_used_count = db.Column(db.Integer, default=0, comment='游客免费额度使用次数')
    last_guest_bonus_time = db.Column(db.DateTime, nullable=True, comment='上次游客赠送时间')
    # 普通用户/会员赠送追踪
    registered_bonus_used_count = db.Column(db.Integer, default=0, comment='普通用户/会员免费额度使用次数')
    last_registered_bonus_time = db.Column(db.DateTime, nullable=True, comment='上次普通用户/会员赠送时间')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 索引
    __table_args__ = (
        Index('idx_openid', 'openid'),
        Index('idx_phone', 'phone'),
        Index('idx_device_id', 'device_id'),
        Index('idx_member_level', 'member_level'),
        Index('idx_is_deactivated', 'is_deactivated'),
        Index('idx_user_type', 'user_type'),
        Index('idx_referral_code', 'referral_code'),
        {'comment': '用户表'}
    )

    def to_dict(self):
        """转换为字典"""
        from auth import is_developer
        return {
            'id': self.id,
            'openid': self.openid,
            'unionid': self.unionid,
            'phone': self.phone,
            'device_id': self.device_id,
            'nickname': self.nickname,
            'avatar_url': self.avatar_url,
            'member_level': self.member_level,
            'member_expire_at': self.member_expire_at.isoformat() if self.member_expire_at else None,
            'scissor_hairs': self.scissor_hairs,
            'comb_hairs': self.comb_hairs,
            'total_hairs': self.scissor_hairs + self.comb_hairs,
            'total_recharge': float(self.total_recharge),
            'total_consumed_hairs': self.total_consumed_hairs,
            'user_type': self.user_type,
            'is_vip': self.is_vip(),
            'is_member_expired': self.is_member_expired(),
            'guest_bonus_used_count': self.guest_bonus_used_count,
            'last_guest_bonus_time': self.last_guest_bonus_time.isoformat() if self.last_guest_bonus_time else None,
            'registered_bonus_used_count': self.registered_bonus_used_count,
            'last_registered_bonus_time': self.last_registered_bonus_time.isoformat() if self.last_registered_bonus_time else None,
            'is_developer': is_developer(self.id),
            'cash_balance': float(self.cash_balance),
            'total_referral_earnings': float(self.total_referral_earnings),
            'referral_code': self.referral_code,
            'referral_count': self.referral_count
        }

    def is_vip(self):
        """是否为vip 会员"""
        return self.member_level == 'vip' and not self.is_member_expired()


    def is_premium(self):
        """是否为 premium 会员（陪跑会员）"""
        return self.is_vip()

    def is_member_expired(self):
        """会员是否已过期"""
        if self.member_level != 'vip':
            return True
        if not self.member_expire_at:
            return True
        return datetime.now() > self.member_expire_at

    def get_total_hairs(self):
        """获取总头发丝数量"""
        return self.scissor_hairs + self.comb_hairs

    def has_enough_hairs(self, required):
        """检查头发丝是否足够"""
        return self.get_total_hairs() >= required


class RechargeRecord(db.Model):
    """充值记录表"""
    __tablename__ = 'recharge_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    order_no = db.Column(db.String(64), unique=True, nullable=False, comment='订单号')
    amount = db.Column(db.Numeric(10, 2), nullable=False, comment='充值金额')
    scissor_hairs = db.Column(db.Integer, nullable=False, comment='剪刀卡槽增加头发丝')
    comb_hairs = db.Column(db.Integer, nullable=False, comment='梳子卡槽增加头发丝')
    payment_method = db.Column(db.Enum('wechat', 'alipay', 'unionpay', 'wechat_virtual'), nullable=False, comment='支付方式')
    payment_status = db.Column(db.Enum('pending', 'success', 'failed', 'refunded'), default='pending', comment='支付状态')
    transaction_id = db.Column(db.String(128), nullable=True, comment='第三方交易号')
    paid_at = db.Column(db.DateTime, nullable=True, comment='支付时间')
    refund_no = db.Column(db.String(64), nullable=True, comment='退款单号')
    refund_amount = db.Column(db.Numeric(10, 2), nullable=True, comment='退款金额')
    refunded_at = db.Column(db.DateTime, nullable=True, comment='退款时间')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    # 关联
    user = db.relationship('User', backref=db.backref('recharge_records', lazy=True))

    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_order_no', 'order_no'),
        Index('idx_payment_status', 'payment_status'),
        {'comment': '充值记录表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'order_no': self.order_no,
            'amount': float(self.amount),
            'scissor_hairs': self.scissor_hairs,
            'comb_hairs': self.comb_hairs,
            'total_hairs': self.scissor_hairs + self.comb_hairs,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'transaction_id': self.transaction_id,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'created_at': self.created_at.isoformat()
        }


class MemberOrder(db.Model):
    """会员订单表"""
    __tablename__ = 'member_orders'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    order_no = db.Column(db.String(64), unique=True, nullable=False, comment='订单号')
    member_level = db.Column(db.String(20), nullable=False, default='vip', comment='会员等级')
    amount = db.Column(db.Numeric(10, 2), nullable=False, comment='会员费用')
    bonus_hairs = db.Column(db.Integer, default=0, comment='赠送头发丝')
    payment_method = db.Column(db.Enum('wechat', 'alipay', 'unionpay', 'wechat_virtual'), nullable=False, comment='支付方式')
    payment_status = db.Column(db.Enum('pending', 'success', 'failed', 'refunded'), default='pending', comment='支付状态')
    transaction_id = db.Column(db.String(128), nullable=True, comment='第三方交易号')
    paid_at = db.Column(db.DateTime, nullable=True, comment='支付时间')
    expire_at = db.Column(db.DateTime, nullable=True, comment='会员到期时间')
    refund_amount = db.Column(db.Numeric(10, 2), nullable=True, comment='退款金额')
    refunded_at = db.Column(db.DateTime, nullable=True, comment='退款时间')
    refund_days = db.Column(db.Integer, nullable=True, comment='退款天数(会员剩余天数)')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    # 关联
    user = db.relationship('User', backref=db.backref('member_orders', lazy=True))

    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_order_no', 'order_no'),
        {'comment': '会员订单表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'order_no': self.order_no,
            'member_level': self.member_level,
            'amount': float(self.amount),
            'bonus_hairs': self.bonus_hairs,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'transaction_id': self.transaction_id,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'expire_at': self.expire_at.isoformat() if self.expire_at else None,
            'refund_amount': float(self.refund_amount) if self.refund_amount else None,
            'refunded_at': self.refunded_at.isoformat() if self.refunded_at else None,
            'refund_days': self.refund_days,
            'created_at': self.created_at.isoformat()
        }


class ConsumptionRecord(db.Model):
    """消费记录表"""
    __tablename__ = 'consumption_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    task_id = db.Column(db.String(64), nullable=False, comment='任务ID')
    service_type = db.Column(db.Enum('hair_segment', 'face_merge', 'sketch', 'combined', 'fm_step', 'sk_step'), nullable=False, comment='服务类型')
    hairs_consumed = db.Column(db.Integer, nullable=False, comment='消耗头发丝数量')
    scissor_deducted = db.Column(db.Integer, default=0, comment='剪刀卡槽扣除')
    comb_deducted = db.Column(db.Integer, default=0, comment='梳子卡槽扣除')
    status = db.Column(db.Enum('success', 'failed'), default='success', comment='状态')
    result_url = db.Column(db.String(500), nullable=True, comment='结果图片URL')
    sketch_url = db.Column(db.String(500), nullable=True, comment='素描图片URL')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    # 关联
    user = db.relationship('User', backref=db.backref('consumption_records', lazy=True))

    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_task_id', 'task_id'),
        Index('idx_created_at', 'created_at'),
        {'comment': '消费记录表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'service_type': self.service_type,
            'hairs_consumed': self.hairs_consumed,
            'scissor_deducted': self.scissor_deducted,
            'comb_deducted': self.comb_deducted,
            'status': self.status,
            'result_url': self.result_url,
            'sketch_url': self.sketch_url,
            'created_at': self.created_at.isoformat()
        }


class HistoryRecord(db.Model):
    """历史记录表（仅vip 会员）"""
    __tablename__ = 'history_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    task_id = db.Column(db.String(64), nullable=False, comment='任务ID')
    service_type = db.Column(db.Enum('hair_segment', 'face_merge', 'sketch', 'combined', 'fm_step', 'sk_step'), nullable=False, comment='服务类型')
    original_hair_url = db.Column(db.String(500), nullable=True, comment='原始发型图URL')
    customer_image_url = db.Column(db.String(500), nullable=True, comment='客户照片URL')
    result_url = db.Column(db.String(500), nullable=True, comment='结果图片URL')
    sketch_url = db.Column(db.String(500), nullable=True, comment='素描图片URL')
    model_version = db.Column(db.String(20), nullable=True, comment='模型版本')
    face_blend_ratio = db.Column(db.Numeric(3, 2), nullable=True, comment='脸型融合权重')
    expire_at = db.Column(db.DateTime, nullable=False, comment='过期时间（45天后自动删除）')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    # 关联
    user = db.relationship('User', backref=db.backref('history_records', lazy=True))

    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_expire_at', 'expire_at'),
        Index('idx_task_id', 'task_id'),
        {'comment': '历史记录表'}
    )

    def to_dict(self):
        """转换为字典"""
        from datetime import datetime
        now = datetime.now()
        is_expired = self.expire_at < now if self.expire_at else False
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'service_type': self.service_type,
            'original_hair_url': self.original_hair_url,
            'customer_image_url': self.customer_image_url,
            'result_url': self.result_url,
            'result_image': self.result_url,  # 前端兼容字段
            'sketch_url': self.sketch_url,
            'model_version': self.model_version,
            'face_blend_ratio': float(self.face_blend_ratio) if self.face_blend_ratio else None,
            'expire_at': self.expire_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'is_expired': is_expired
        }


class MemberReminder(db.Model):
    """会员到期提醒表"""
    __tablename__ = 'member_reminders'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    member_expire_at = db.Column(db.DateTime, nullable=False, comment='会员到期时间')
    reminder_type = db.Column(db.Enum('15days', '7days', '1day'), nullable=False, comment='提醒类型')
    sent_at = db.Column(db.DateTime, default=datetime.now, comment='发送时间')
    status = db.Column(db.Enum('sent', 'failed'), default='sent', comment='状态')

    # 关联
    user = db.relationship('User', backref=db.backref('member_reminders', lazy=True))

    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_member_expire_at', 'member_expire_at'),
        {'comment': '会员到期提醒表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'member_expire_at': self.member_expire_at.isoformat(),
            'reminder_type': self.reminder_type,
            'sent_at': self.sent_at.isoformat(),
            'status': self.status
        }


class InsufficientReminder(db.Model):
    """余额不足提醒表"""
    __tablename__ = 'insufficient_reminders'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    reminded_at = db.Column(db.DateTime, default=datetime.now, comment='提醒时间')
    bonus_added = db.Column(db.Boolean, default=False, comment='是否已赠送')
    bonus_hairs = db.Column(db.Integer, default=0, comment='赠送头发丝数量')
    bonus_added_at = db.Column(db.DateTime, nullable=True, comment='赠送时间')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    # 关联
    user = db.relationship('User', backref=db.backref('insufficient_reminders', lazy=True))

    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_reminded_at', 'reminded_at'),
        {'comment': '余额不足提醒表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'reminded_at': self.reminded_at.isoformat(),
            'bonus_added': self.bonus_added,
            'bonus_hairs': self.bonus_hairs,
            'bonus_added_at': self.bonus_added_at.isoformat() if self.bonus_added_at else None,
            'created_at': self.created_at.isoformat()
        }


class Device(db.Model):
    """设备管理表"""
    __tablename__ = 'devices'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    device_id = db.Column(db.String(64), unique=True, nullable=False, comment='设备ID')
    device_name = db.Column(db.String(100), nullable=False, comment='设备名称')
    device_type = db.Column(db.String(20), nullable=True, comment='设备类型')
    is_primary = db.Column(db.Boolean, default=False, comment='是否主设备')
    bound_at = db.Column(db.DateTime, default=datetime.now, comment='绑定时间')
    last_active_at = db.Column(db.DateTime, default=datetime.now, comment='最后活跃时间')

    # 关联
    user = db.relationship('User', backref=db.backref('devices', lazy=True))

    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_device_id', 'device_id'),
        {'comment': '设备管理表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'is_primary': self.is_primary,
            'bound_at': self.bound_at.isoformat() if self.bound_at else None,
            'last_active_at': self.last_active_at.isoformat() if self.last_active_at else None
        }


class GuestBonusRecord(db.Model):
    """游客免费额度赠送记录表"""
    __tablename__ = 'guest_bonus_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    openid = db.Column(db.String(128), nullable=False, comment='微信openid')
    bonus_type = db.Column(db.Enum('initial', 'auto_renew'), nullable=False, comment='赠送类型')
    hairs_added = db.Column(db.Integer, default=0, comment='赠送头发丝数量')
    trigger_reason = db.Column(db.String(50), default='insufficient_balance', comment='触发原因')
    reminded_at = db.Column(db.DateTime, nullable=False, comment='提醒时间')
    bonus_added_at = db.Column(db.DateTime, nullable=True, comment='赠送时间')
    next_check_time = db.Column(db.DateTime, nullable=True, comment='下次检查时间')
    is_completed = db.Column(db.Boolean, default=False, comment='是否已完成')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关联
    user = db.relationship('User', backref=db.backref('guest_bonus_records', lazy=True))

    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_openid', 'openid'),
        Index('idx_bonus_type', 'bonus_type'),
        Index('idx_is_completed', 'is_completed'),
        Index('idx_next_check_time', 'next_check_time'),
        {'comment': '游客免费额度赠送记录表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'openid': self.openid,
            'bonus_type': self.bonus_type,
            'hairs_added': self.hairs_added,
            'trigger_reason': self.trigger_reason,
            'reminded_at': self.reminded_at.isoformat() if self.reminded_at else None,
            'bonus_added_at': self.bonus_added_at.isoformat() if self.bonus_added_at else None,
            'next_check_time': self.next_check_time.isoformat() if self.next_check_time else None,
            'is_completed': self.is_completed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserBonusRecord(db.Model):
    """普通用户/会员免费额度赠送记录表"""
    __tablename__ = 'user_bonus_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    user_type_at_bonus = db.Column(db.Enum('normal', 'vip'), nullable=False, comment='赠送时用户类型')
    bonus_type = db.Column(db.Enum('auto_renew'), nullable=False, comment='赠送类型')
    hairs_added = db.Column(db.Integer, default=0, comment='赠送头发丝数量')
    reminded_at = db.Column(db.DateTime, nullable=False, comment='提醒时间')
    next_check_time = db.Column(db.DateTime, nullable=True, comment='下次检查时间')
    bonus_added_at = db.Column(db.DateTime, nullable=True, comment='赠送时间')
    is_completed = db.Column(db.Boolean, default=False, comment='是否已完成')
    has_consumption_before_bonus = db.Column(db.Boolean, default=False, comment='赠送前是否有消费')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关联
    user = db.relationship('User', backref=db.backref('user_bonus_records', lazy=True))

    # 索引
    __table_args__ = (
        Index('idx_user_reminded', 'user_id', 'reminded_at'),
        Index('idx_next_check', 'next_check_time', 'is_completed'),
        {'comment': '普通用户/会员免费额度赠送记录表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_type_at_bonus': self.user_type_at_bonus,
            'bonus_type': self.bonus_type,
            'hairs_added': self.hairs_added,
            'reminded_at': self.reminded_at.isoformat() if self.reminded_at else None,
            'next_check_time': self.next_check_time.isoformat() if self.next_check_time else None,
            'bonus_added_at': self.bonus_added_at.isoformat() if self.bonus_added_at else None,
            'is_completed': self.is_completed,
            'has_consumption_before_bonus': self.has_consumption_before_bonus,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Message(db.Model):
    """客户留言表"""
    __tablename__ = 'messages'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, comment='用户姓名')
    phone = db.Column(db.String(20), nullable=False, comment='联系电话')
    content = db.Column(db.Text, nullable=False, comment='留言内容')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    # 索引
    __table_args__ = (
        Index('idx_created_at', 'created_at'),
        {'comment': '客户留言表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ChatMessage(db.Model):
    """实时聊天消息表"""
    __tablename__ = 'chat_messages'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='关联用户ID')
    sender_type = db.Column(db.Enum('user', 'admin'), nullable=False, comment='发送者类型')
    content = db.Column(db.Text, nullable=False, comment='消息内容')
    is_read = db.Column(db.Boolean, default=False, comment='是否已读（对admin消息而言）')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 索引
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_user_unread', 'user_id', 'sender_type', 'is_read'),
        {'comment': '实时聊天消息表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'sender_type': self.sender_type,
            'content': self.content,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ReferralRelation(db.Model):
    """推广关系表"""
    __tablename__ = 'referral_relations'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    referrer_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='推广人用户ID')
    referee_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='被推广人用户ID')
    scene = db.Column(db.String(128), nullable=False, comment='小程序码scene参数')
    status = db.Column(db.Enum('pending', 'active', 'rewarded'), default='pending', comment='状态')
    referee_registered_at = db.Column(db.DateTime, nullable=True, comment='被推广人注册时间')
    commission_paid_at = db.Column(db.DateTime, nullable=True, comment='佣金发放时间')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    # 关联
    referrer = db.relationship('User', foreign_keys=[referrer_id], backref=db.backref('referrals_made', lazy='dynamic'))
    referee = db.relationship('User', foreign_keys=[referee_id], backref=db.backref('referrals_received', lazy='dynamic'))

    __table_args__ = (
        Index('idx_referrer_id', 'referrer_id'),
        Index('idx_scene', 'scene'),
        Index('idx_status', 'status'),
        {'comment': '推广关系表'}
    )

    def to_dict(self):
        return {
            'id': self.id,
            'referrer_id': self.referrer_id,
            'referee_id': self.referee_id,
            'scene': self.scene,
            'status': self.status,
            'referee_registered_at': self.referee_registered_at.isoformat() if self.referee_registered_at else None,
            'commission_paid_at': self.commission_paid_at.isoformat() if self.commission_paid_at else None,
            'created_at': self.created_at.isoformat()
        }


class CommissionRecord(db.Model):
    """佣金记录表"""
    __tablename__ = 'commission_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='推广人用户ID')
    referee_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='好友用户ID')
    referral_id = db.Column(db.BigInteger, db.ForeignKey('referral_relations.id'), nullable=False, comment='推广关系ID')
    amount = db.Column(db.Numeric(10, 2), default=0.03, comment='佣金金额(元)')
    reason = db.Column(db.String(100), default='friend_completed_2_sketches', comment='佣金原因')
    status = db.Column(db.Enum('pending', 'paid'), default='paid', comment='状态')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('commission_records', lazy='dynamic'))

    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_referral_id', 'referral_id'),
        {'comment': '佣金记录表'}
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'referee_id': self.referee_id,
            'referral_id': self.referral_id,
            'amount': float(self.amount),
            'reason': self.reason,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }


class CashWithdrawalRecord(db.Model):
    """提现记录表"""
    __tablename__ = 'cash_withdrawal_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum('pending', 'processing', 'success', 'failed'), default='pending')
    wechat_batch_no = db.Column(db.String(64), nullable=True, comment='微信批次号')
    wechat_payment_no = db.Column(db.String(64), nullable=True, comment='微信企业付款单号')
    fail_reason = db.Column(db.String(255), nullable=True, comment='失败原因')
    created_at = db.Column(db.DateTime, default=datetime.now)
    processed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('cash_withdrawal_records', lazy='dynamic'))

    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_status', 'status'),
        {'comment': '提现记录表'}
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': float(self.amount),
            'status': self.status,
            'wechat_batch_no': self.wechat_batch_no,
            'wechat_payment_no': self.wechat_payment_no,
            'fail_reason': self.fail_reason,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }


class CashConsumptionRecord(db.Model):
    """存钱罐本地消费记录表"""
    __tablename__ = 'cash_consumption_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    cash_spent = db.Column(db.Numeric(10, 2), nullable=False)
    hairs_received = db.Column(db.Integer, nullable=False)
    exchange_rate = db.Column(db.String(50), nullable=True, comment='兑换比例描述')
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref=db.backref('cash_consumption_records', lazy='dynamic'))

    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        {'comment': '存钱罐本地消费记录表'}
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'cash_spent': float(self.cash_spent),
            'hairs_received': self.hairs_received,
            'exchange_rate': self.exchange_rate,
            'created_at': self.created_at.isoformat()
        }


class RefundApplication(db.Model):
    """退款申请表"""
    __tablename__ = 'refund_applications'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    applicant_name = db.Column(db.String(50), nullable=False, comment='申请人姓名')
    applicant_phone = db.Column(db.String(20), nullable=False, comment='申请人电话')
    applicant_wechat_id = db.Column(db.String(100), nullable=True, comment='申请人微信号')
    refund_type = db.Column(db.Enum('recharge', 'membership'), nullable=False, comment='退款类型')
    refund_amount = db.Column(db.Numeric(10, 2), nullable=False, comment='申请退款金额')
    reason = db.Column(db.Text, nullable=False, comment='退款原因')
    consumption_summary = db.Column(db.JSON, nullable=True, comment='消费使用情况摘要')
    suggestions = db.Column(db.Text, nullable=True, comment='对本项目的建议')
    status = db.Column(db.Enum('pending', 'approved', 'rejected'), default='pending', comment='审批状态')
    approved_by = db.Column(db.BigInteger, nullable=True, comment='审批人ID')
    approved_at = db.Column(db.DateTime, nullable=True, comment='审批时间')
    rejection_reason = db.Column(db.Text, nullable=True, comment='拒绝原因')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='申请时间')

    user = db.relationship('User', backref=db.backref('refund_applications', lazy=True))

    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
        {'comment': '退款申请表'}
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'applicant_name': self.applicant_name,
            'applicant_phone': self.applicant_phone,
            'applicant_wechat_id': self.applicant_wechat_id,
            'refund_type': self.refund_type,
            'refund_amount': float(self.refund_amount),
            'reason': self.reason,
            'consumption_summary': self.consumption_summary,
            'suggestions': self.suggestions,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'created_at': self.created_at.isoformat()
        }


class FinancialRecord(db.Model):
    """财务流水记录表"""
    __tablename__ = 'financial_records'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    record_type = db.Column(db.Enum('recharge', 'member_purchase', 'refund', 'commission', 'withdrawal', 'cash_consumption'), nullable=False, comment='记录类型')
    amount = db.Column(db.Numeric(10, 2), nullable=False, comment='金额(元)，正数=收入，负数=支出')
    description = db.Column(db.String(255), nullable=False, comment='描述')
    payment_method = db.Column(db.String(50), nullable=True, comment='支付方式')
    related_id = db.Column(db.BigInteger, nullable=True, comment='关联记录ID')
    related_type = db.Column(db.String(50), nullable=True, comment='关联记录类型')
    hairs_changed = db.Column(db.Integer, nullable=True, comment='关联发丝变动数量')
    status = db.Column(db.Enum('success', 'pending', 'failed'), default='success', comment='状态')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    # 索引
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_user_type', 'user_id', 'record_type'),
        Index('idx_status', 'status'),
        {'comment': '财务流水记录表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'record_type': self.record_type,
            'amount': float(self.amount),
            'description': self.description,
            'payment_method': self.payment_method,
            'related_id': self.related_id,
            'related_type': self.related_type,
            'hairs_changed': self.hairs_changed,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ==================== 认证服务 ====================

class AuthService:
    """认证服务"""

    def __init__(self):
        self.config = get_config()
        self.jwt_secret_key = self.config.JWT_SECRET_KEY
        self.jwt_access_token_expires = self.config.JWT_ACCESS_TOKEN_EXPIRES

    def generate_token(self, user_id):
        """生成 JWT Token"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=self.jwt_access_token_expires),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, self.jwt_secret_key, algorithm="HS256")
        return token

    def decode_token(self, token):
        """解码 JWT Token"""
        try:
            payload = jwt.decode(token, self.jwt_secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_current_user(self):
        """获取当前登录用户"""
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return None

        payload = self.decode_token(token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        user = User.query.get(user_id)
        return user

    def wechat_login(self, code, device_info=None, nickname=None, avatar_url=None):
        """微信登录（支持游客模式、普通用户模式、会员模式）"""
        config = get_config()

        # 调用微信API获取openid
        if config.WECHAT_APP_ID and config.WECHAT_APP_SECRET:
            url = (
                f"https://api.weixin.qq.com/sns/jscode2session"
                f"?appid={config.WECHAT_APP_ID}"
                f"&secret={config.WECHAT_APP_SECRET}"
                f"&js_code={code}"
                f"&grant_type=authorization_code"
            )
            resp = requests.get(url, timeout=10)
            wx_data = resp.json()

            if "errcode" in wx_data and wx_data["errcode"] != 0:
                return None, {"error": "微信登录失败", "code": 4001}

            openid = wx_data.get("openid")
            unionid = wx_data.get("unionid")
        else:
            # 开发模式：使用测试openid
            openid = f"test_openid_{code}"
            unionid = None

        # 查找用户
        user = User.query.filter_by(openid=openid).first()

        if user:
            # 老用户
            is_new_user = False
            # 更新昵称和头像（如果前端传来）
            if nickname:
                user.nickname = nickname
            if avatar_url:
                user.avatar_url = avatar_url
            db.session.commit()
        else:
            # 新用户：注册（赠送1000头发丝）
            is_new_user = True
            user = register_user(
                openid=openid,
                unionid=unionid,
                nickname=nickname,
                avatar_url=avatar_url,
            )

        # 生成token
        token = self.generate_token(user.id)

        # 更新设备信息
        if device_info:
            self._update_device(user.id, device_info)

        return user, {
            "token": token,
            "user": user.to_dict(),
            "is_new_user": is_new_user,
        }

    def _update_device(self, user_id, device_info):
        """更新设备信息"""
        device_id = device_info.get("device_id")
        if not device_id:
            return

        device = Device.query.filter_by(device_id=device_id).first()
        if device:
            device.last_active_at = datetime.now()
            device.user_id = user_id
        else:
            device = Device(
                user_id=user_id,
                device_id=device_id,
                device_name=device_info.get("device_name", "Unknown"),
                device_type=device_info.get("device_type", "unknown"),
                is_primary=False,
            )
            db.session.add(device)

        db.session.commit()


def login_required(f):
    """登录验证装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_service = AuthService()
        user = auth_service.get_current_user()

        if not user:
            return jsonify({"error": "未登录或登录已过期", "code": 401}), 401

        # 检查是否注销
        if user.is_deactivated:
            return jsonify({"error": "账号已注销", "code": 403}), 403

        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function


def register_user(openid=None, unionid=None, phone=None, nickname=None, avatar_url=None):
    """注册新用户（赠送1000头发丝）"""
    from config import INITIAL_BONUS_HAIR_COUNT

    user = User(
        openid=openid,
        unionid=unionid,
        phone=phone,
        nickname=nickname,
        avatar_url=avatar_url,
        scissor_hairs=INITIAL_BONUS_HAIR_COUNT,
        comb_hairs=0,
    )
    db.session.add(user)
    db.session.commit()
    return user


def grant_guest_initial_bonus(user_id, hairs=198):
    """赠送游客初始头发丝（用于首次进入）"""
    user = User.query.get(user_id)
    if not user:
        return False

    user.comb_hairs += hairs
    db.session.commit()
    return True


# ==================== 开发者权限 ====================

def is_developer_mode_enabled():
    """判断开发者模式是否已启用"""
    from config import DEVELOPER_MODE_ENABLED
    return DEVELOPER_MODE_ENABLED


def is_developer(user_id=None):
    """判断是否为开发者测试账号"""
    from config import DEVELOPER_ACCOUNTS

    if not is_developer_mode_enabled():
        return False

    if not DEVELOPER_ACCOUNTS:
        return False

    if user_id is None:
        auth_service = AuthService()
        user = auth_service.get_current_user()
        if not user:
            return False
        user_id = user.id

    return user_id in DEVELOPER_ACCOUNTS


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

        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function
