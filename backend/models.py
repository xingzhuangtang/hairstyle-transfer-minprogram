#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型
使用SQLAlchemy ORM
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index

db = SQLAlchemy()


class User(db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    openid = db.Column(db.String(128), unique=True, nullable=True, comment='微信openid')
    unionid = db.Column(db.String(128), unique=True, nullable=True, comment='微信unionid')
    phone = db.Column(db.String(20), unique=True, nullable=True, comment='手机号')
    nickname = db.Column(db.String(100), nullable=True, comment='昵称')
    avatar_url = db.Column(db.String(500), nullable=True, comment='头像URL')
    member_level = db.Column(db.Enum('normal', 'vip'), default='normal', comment='会员等级')
    member_expire_at = db.Column(db.DateTime, nullable=True, comment='会员到期时间')
    scissor_hairs = db.Column(db.Integer, default=0, comment='剪刀卡槽头发丝数量')
    comb_hairs = db.Column(db.Integer, default=0, comment='梳子卡槽头发丝数量')
    total_recharge = db.Column(db.Numeric(10, 2), default=0.00, comment='累计充值金额')
    total_consumed_hairs = db.Column(db.Integer, default=0, comment='累计消耗头发丝')
    is_deactivated = db.Column(db.Boolean, default=False, comment='是否已注销')
    deactivated_at = db.Column(db.DateTime, nullable=True, comment='注销时间')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 索引
    __table_args__ = (
        Index('idx_openid', 'openid'),
        Index('idx_phone', 'phone'),
        Index('idx_member_level', 'member_level'),
        Index('idx_is_deactivated', 'is_deactivated'),
        {'comment': '用户表'}
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'openid': self.openid,
            'unionid': self.unionid,
            'phone': self.phone,
            'nickname': self.nickname,
            'avatar_url': self.avatar_url,
            'member_level': self.member_level,
            'member_expire_at': self.member_expire_at.isoformat() if self.member_expire_at else None,
            'scissor_hairs': self.scissor_hairs,
            'comb_hairs': self.comb_hairs,
            'total_hairs': self.scissor_hairs + self.comb_hairs,
            'total_recharge': float(self.total_recharge),
            'total_consumed_hairs': self.total_consumed_hairs,
            'is_vip': self.is_vip(),
            'is_member_expired': self.is_member_expired()
        }
    
    def is_vip(self):
        """是否为vip 会员"""
        return self.member_level == 'vip' and not self.is_member_expired()
    
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
    payment_method = db.Column(db.Enum('wechat', 'alipay', 'unionpay'), nullable=False, comment='支付方式')
    payment_status = db.Column(db.Enum('pending', 'success', 'failed', 'refunded'), default='pending', comment='支付状态')
    transaction_id = db.Column(db.String(128), nullable=True, comment='第三方交易号')
    paid_at = db.Column(db.DateTime, nullable=True, comment='支付时间')
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
    member_level = db.Column(db.Enum('normal', 'vip'), nullable=False, comment='会员等级')
    amount = db.Column(db.Numeric(10, 2), nullable=False, comment='会员费用')
    bonus_hairs = db.Column(db.Integer, default=0, comment='赠送头发丝')
    payment_method = db.Column(db.Enum('wechat', 'alipay', 'unionpay'), nullable=False, comment='支付方式')
    payment_status = db.Column(db.Enum('pending', 'success', 'failed'), default='pending', comment='支付状态')
    transaction_id = db.Column(db.String(128), nullable=True, comment='第三方交易号')
    paid_at = db.Column(db.DateTime, nullable=True, comment='支付时间')
    expire_at = db.Column(db.DateTime, nullable=True, comment='会员到期时间')
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
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'service_type': self.service_type,
            'original_hair_url': self.original_hair_url,
            'customer_image_url': self.customer_image_url,
            'result_url': self.result_url,
            'sketch_url': self.sketch_url,
            'model_version': self.model_version,
            'face_blend_ratio': float(self.face_blend_ratio) if self.face_blend_ratio else None,
            'expire_at': self.expire_at.isoformat(),
            'created_at': self.created_at.isoformat()
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


