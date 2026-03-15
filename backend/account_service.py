#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账户服务模块
处理注册赠送、余额不足自动赠送、账户注销等功能
"""

from datetime import datetime, timedelta
from models import db, User, ConsumptionRecord, InsufficientReminder
from config import get_config


class AccountService:
    """账户服务"""

    def __init__(self):
        self.config = get_config()
        # 注册赠送头发丝数量
        self.register_bonus_hairs = 1000
        # 普通用户 4 小时未充值赠送数量
        self.normal_user_bonus_hairs = 188
        # 陪跑用户 4 小时未充值赠送数量
        self.vip_user_bonus_hairs = 98
        # 一年之内最多赠送次数
        self.max_bonus_times_per_year = 36

    def register_user(self, user):
        """
        用户注册时自动赠送头发丝

        Args:
            user: User 对象

        Returns:
            dict: {success, error}
        """
        try:
            # 注册时自动赠送 1000 根头发丝到梳子卡槽
            user.comb_hairs += self.register_bonus_hairs

            db.session.commit()

            print(f"✅ 用户注册赠送头发丝：user_id={user.id}, bonus={self.register_bonus_hairs}")

            return {
                'success': True,
                'bonus_hairs': self.register_bonus_hairs
            }

        except Exception as e:
            db.session.rollback()
            print(f"❌ 用户注册赠送头发丝失败：{e}")
            return {
                'success': False,
                'error': str(e)
            }

    def check_and_add_bonus_for_insufficient(self, user):
        """
        检查并添加余额不足时的自动赠送头发丝

        Args:
            user: User 对象

        Returns:
            dict: {success, bonus_added, error}
        """
        try:
            # 查找最近一次余额不足提醒的记录
            from models import InsufficientReminder

            # 查找最近一次余额不足提醒
            last_reminder = InsufficientReminder.query.filter_by(
                user_id=user.id
            ).order_by(InsufficientReminder.reminded_at.desc()).first()

            # 如果没有记录过，或者距离上次提醒已经超过 4 小时
            should_add_bonus = False

            if not last_reminder:
                # 第一次余额不足，记录提醒时间
                reminder = InsufficientReminder(
                    user_id=user.id,
                    reminded_at=datetime.now()
                )
                db.session.add(reminder)
                db.session.commit()

                print(f"✅ 记录余额不足提醒：user_id={user.id}")
                return {
                    'success': True,
                    'bonus_added': False,
                    'message': '已记录余额不足提醒时间'
                }

            # 检查距离上次提醒是否超过 4 小时
            hours_since_last_reminder = (datetime.now() - last_reminder.reminded_at).total_seconds() / 3600

            if hours_since_last_reminder >= 4:
                # 超过 4 小时，检查是否在 4 小时内充值
                # 查找 4 小时内的充值记录
                from models import RechargeRecord

                four_hours_ago = datetime.now() - timedelta(hours=4)
                recent_recharge = RechargeRecord.query.filter(
                    RechargeRecord.user_id == user.id,
                    RechargeRecord.payment_status == 'success',
                    RechargeRecord.paid_at >= four_hours_ago
                ).first()

                if not recent_recharge:
                    # 4 小时内没有充值，检查一年内的赠送次数
                    one_year_ago = datetime.now() - timedelta(days=365)
                    bonus_count = InsufficientReminder.query.filter(
                        InsufficientReminder.user_id == user.id,
                        InsufficientReminder.bonus_added_at >= one_year_ago,
                        InsufficientReminder.bonus_added == True
                    ).count()

                    if bonus_count < self.max_bonus_times_per_year:
                        # 一年内赠送次数少于 36 次，可以赠送
                        bonus_hairs = self.normal_user_bonus_hairs if user.member_level == 'normal' else self.vip_user_bonus_hairs

                        user.comb_hairs += bonus_hairs

                        # 更新提醒记录
                        last_reminder.bonus_added = True
                        last_reminder.bonus_hairs = bonus_hairs
                        last_reminder.bonus_added_at = datetime.now()

                        db.session.commit()

                        should_add_bonus = True

                        print(f"✅ 余额不足自动赠送头发丝：user_id={user.id}, bonus={bonus_hairs}, "
                              f"type={'normal' if user.member_level == 'normal' else 'vip'}")
                    else:
                        # 一年内已赠送 36 次，不再赠送
                        print(f"⚠️ 用户已达到年度赠送次数上限：user_id={user.id}")

                        # 更新提醒记录
                        last_reminder.bonus_added = False
                        db.session.commit()

            # 记录新的余额不足提醒
            if not should_add_bonus:
                reminder = InsufficientReminder(
                    user_id=user.id,
                    reminded_at=datetime.now()
                )
                db.session.add(reminder)
                db.session.commit()

                return {
                    'success': True,
                    'bonus_added': False,
                    'message': '已记录余额不足提醒时间'
                }

            return {
                'success': True,
                'bonus_added': should_add_bonus,
                'bonus_hairs': last_reminder.bonus_hairs if should_add_bonus and last_reminder.bonus_hairs else 0
            }

        except Exception as e:
            db.session.rollback()
            print(f"❌ 检查余额不足自动赠送失败：{e}")
            return {
                'success': False,
                'error': str(e)
            }

    def deactivate_account(self, user):
        """
        注销账户

        Args:
            user: User 对象

        Returns:
            dict: {success, error}
        """
        try:
            # 检查是否已经有注销记录
            if user.is_deactivated:
                return {
                    'success': False,
                    'error': '账户已注销'
                }

            # 记录注销前的余额
            final_scissor_hairs = user.scissor_hairs
            final_comb_hairs = user.comb_hairs
            final_total_hairs = user.get_total_hairs()
            final_total_recharge = float(user.total_recharge)

            # 标记账户为已注销
            user.is_deactivated = True
            user.deactivated_at = datetime.now()

            # 头发丝归零
            user.scissor_hairs = 0
            user.comb_hairs = 0

            # 清空 openid 和 phone（可选，根据需求）
            # user.openid = None
            # user.phone = None

            db.session.commit()

            print(f"✅ 账户注销成功：user_id={user.id}, "
                  f"scissor={final_scissor_hairs}, comb={final_comb_hairs}, "
                  f"total={final_total_hairs}, recharge={final_total_recharge}")

            return {
                'success': True,
                'message': '账户已注销',
                'final_balance': {
                    'scissor_hairs': final_scissor_hairs,
                    'comb_hairs': final_comb_hairs,
                    'total_hairs': final_total_hairs,
                    'total_recharge': final_total_recharge
                }
            }

        except Exception as e:
            db.session.rollback()
            print(f"❌ 账户注销失败：{e}")
            return {
                'success': False,
                'error': str(e)
            }
