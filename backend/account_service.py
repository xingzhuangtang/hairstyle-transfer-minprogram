#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账户服务模块
处理注册赠送、余额不足自动赠送、账户注销等功能
"""

from datetime import datetime, timedelta
from models import db, User, ConsumptionRecord, InsufficientReminder, GuestBonusRecord, UserBonusRecord, RechargeRecord
from config import get_config, GUEST_MODE_CONFIG


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

        # 访客模式配置
        self.guest_initial_bonus = GUEST_MODE_CONFIG.get('initial_bonus', 198)
        self.guest_auto_renew_bonus = GUEST_MODE_CONFIG.get('auto_renew_bonus', 198)
        self.guest_max_bonus_per_year = GUEST_MODE_CONFIG.get('max_bonus_per_year', 9)

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

    def _get_guest_bonus_count_this_year(self, user):
        """
        获取用户本年度已使用的游客赠送次数

        Args:
            user: User 对象

        Returns:
            int: 本年度已赠送次数
        """
        year_start = datetime(datetime.now().year, 1, 1)
        count = GuestBonusRecord.query.filter(
            GuestBonusRecord.user_id == user.id,
            GuestBonusRecord.bonus_added_at >= year_start,
            GuestBonusRecord.is_completed == True
        ).count()
        return count

    def grant_guest_initial_bonus(self, user):
        """
        授予游客首次免费额度（198 根梳子发丝）

        Args:
            user: 用户对象（guest 类型）

        Returns:
            dict: {'success': bool, 'hairs': int, 'message': str, 'error': str}
        """
        try:
            # 检查年度上限
            bonus_count = self._get_guest_bonus_count_this_year(user)
            if bonus_count >= self.guest_max_bonus_per_year:
                return {
                    'success': False,
                    'error': '本年度游客免费额度已用完',
                    'code': 'GUEST_BONUS_EXHAUSTED'
                }

            # 检查是否已赠送过
            if user.guest_bonus_used_count > 0:
                return {
                    'success': False,
                    'error': '已享受过游客首次赠送',
                    'code': 'ALREADY_GRANTED'
                }

            # 赠送 198 根梳子发丝
            user.comb_hairs += self.guest_initial_bonus
            user.guest_bonus_used_count = 1
            user.last_guest_bonus_time = datetime.now()

            # 创建赠送记录
            record = GuestBonusRecord(
                user_id=user.id,
                openid=user.openid,
                bonus_type='initial',
                hairs_added=self.guest_initial_bonus,
                trigger_reason='first_visit',
                reminded_at=datetime.now(),
                bonus_added_at=datetime.now(),
                is_completed=True
            )

            db.session.add(record)
            db.session.commit()

            print(f"✅ 游客首次赠送头发丝：user_id={user.id}, openid={user.openid}, "
                  f"bonus={self.guest_initial_bonus}")

            return {
                'success': True,
                'hairs': self.guest_initial_bonus,
                'message': f'游客体验金{self.guest_initial_bonus}根已发放'
            }

        except Exception as e:
            db.session.rollback()
            print(f"❌ 游客首次赠送头发丝失败：{e}")
            return {
                'success': False,
                'error': str(e)
            }

    def handle_guest_insufficient_balance(self, user, cost):
        """
        处理游客余额不足情况

        Args:
            user: 用户对象
            cost: 所需发丝数量

        Returns:
            dict: {
                'action': 'register_or_wait',
                'message': str,
                'next_check_time': datetime | None,
                'record_id': int | None
            }
        """
        try:
            if user.user_type != 'guest':
                return None  # 非游客，走普通用户流程

            # 检查年度上限
            bonus_count = self._get_guest_bonus_count_this_year(user)
            if bonus_count >= self.guest_max_bonus_per_year:
                return {
                    'action': 'register',
                    'message': '本年度游客免费额度已用完，请完成新用户注册，领取额外 1000 根头发丝福利',
                    'code': 'GUEST_BONUS_EXHAUSTED'
                }

            # 创建余额不足提醒记录（4 小时续赠）
            reminder = GuestBonusRecord(
                user_id=user.id,
                openid=user.openid,
                bonus_type='auto_renew',
                hairs_added=self.guest_auto_renew_bonus,
                trigger_reason='insufficient_balance',
                reminded_at=datetime.now(),
                next_check_time=datetime.now() + timedelta(hours=4),
                is_completed=False
            )
            db.session.add(reminder)
            db.session.commit()

            print(f"✅ 游客余额不足提醒：user_id={user.id}, openid={user.openid}, "
                  f"next_check_time={reminder.next_check_time}")

            return {
                'action': 'register_or_wait',
                'message': f'完成新用户注册，领取{self.register_bonus_hairs}根头发丝福利，或 4 小时后继续使用游客免费额度',
                'next_check_time': reminder.next_check_time,
                'record_id': reminder.id
            }

        except Exception as e:
            db.session.rollback()
            print(f"❌ 处理游客余额不足失败：{e}")
            return {
                'action': 'register',
                'message': '系统繁忙，请稍后再试',
                'error': str(e)
            }

    def check_and_grant_guest_bonus(self, user):
        """
        检查并授予游客 4 小时续赠额度

        触发条件：
        1. 用户类型为 guest
        2. 存在未完成的赠送记录
        3. 距离提醒时间已超过 4 小时
        4. 期间未完成新用户注册
        5. 未达到年度上限
        6. 用户实际使用了产品（有消费记录）

        Args:
            user: 用户对象

        Returns:
            dict: {'success': bool, 'hairs': int, 'message': str, 'error': str}
        """
        try:
            # 检查年度上限
            bonus_count = self._get_guest_bonus_count_this_year(user)
            if bonus_count >= self.guest_max_bonus_per_year:
                return {
                    'success': False,
                    'error': '本年度游客免费额度已用完',
                    'code': 'GUEST_BONUS_EXHAUSTED'
                }

            # 查找待处理的赠送记录
            pending_records = GuestBonusRecord.query.filter(
                GuestBonusRecord.user_id == user.id,
                GuestBonusRecord.bonus_type == 'auto_renew',
                GuestBonusRecord.is_completed == False,
                GuestBonusRecord.next_check_time <= datetime.now()
            ).order_by(GuestBonusRecord.reminded_at.desc()).limit(1).all()

            if not pending_records:
                return {
                    'success': False,
                    'error': '没有待处理的赠送记录',
                    'code': 'NO_PENDING_RECORD'
                }

            record = pending_records[0]

            # 检查是否已注册（user_type 变化）
            if user.user_type != 'guest':
                # 用户已注册，取消赠送
                record.is_completed = True
                db.session.commit()
                return {
                    'success': False,
                    'error': '用户已注册，取消游客赠送',
                    'code': 'USER_REGISTERED'
                }

            # 检查是否实际使用过产品（有消费记录）
            has_consumption = ConsumptionRecord.query.filter_by(
                user_id=user.id,
                status='success'
            ).first() is not None

            if not has_consumption:
                # 没有实际使用过产品，不赠送
                return {
                    'success': False,
                    'error': '未检测到产品使用记录',
                    'code': 'NO_CONSUMPTION'
                }

            # 执行赠送
            user.comb_hairs += self.guest_auto_renew_bonus
            user.guest_bonus_used_count += 1
            user.last_guest_bonus_time = datetime.now()

            # 更新记录
            record.bonus_added_at = datetime.now()
            record.is_completed = True

            db.session.commit()

            print(f"✅ 游客 4 小时续赠头发丝：user_id={user.id}, openid={user.openid}, "
                  f"bonus={self.guest_auto_renew_bonus}")

            return {
                'success': True,
                'hairs': self.guest_auto_renew_bonus,
                'message': f'游客免费额度{self.guest_auto_renew_bonus}根已续期'
            }

        except Exception as e:
            db.session.rollback()
            print(f"❌ 检查并授予游客 4 小时续赠额度失败：{e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_registered_bonus_count_this_year(self, user):
        """
        获取用户本年度已使用的普通用户/会员赠送次数

        Args:
            user: User 对象

        Returns:
            int: 本年度已赠送次数
        """
        year_start = datetime(datetime.now().year, 1, 1)
        count = UserBonusRecord.query.filter(
            UserBonusRecord.user_id == user.id,
            UserBonusRecord.bonus_added_at >= year_start,
            UserBonusRecord.is_completed == True
        ).count()
        return count

    def handle_registered_insufficient_balance(self, user, cost):
        """
        处理普通用户/会员余额不足情况

        Args:
            user: 用户对象（registered 或 vip 类型）
            cost: 所需发丝数量

        Returns:
            dict: {
                'action': 'wait',
                'message': str,
                'vip_upgrade_message': str | None,
                'next_check_time': datetime | None,
                'record_id': int | None,
                'annual_limit_reached': bool
            }
        """
        try:
            # 检查年度上限
            bonus_count = self._get_registered_bonus_count_this_year(user)
            if bonus_count >= self.max_bonus_times_per_year:
                return {
                    'action': 'recharge',
                    'message': '本年度免费额度已用完，请充值消费',
                    'vip_upgrade_message': 'Baby 难道你用了 36 计嘛！？还没等到你的到来？？？请记住升级会员更实惠哦！等你啊 baby！！！',
                    'annual_limit_reached': True
                }

            # 创建余额不足提醒记录
            reminder = UserBonusRecord(
                user_id=user.id,
                user_type_at_bonus=user.member_level,
                bonus_type='auto_renew',
                hairs_added=self.normal_user_bonus_hairs if user.member_level == 'normal' else self.vip_user_bonus_hairs,
                reminded_at=datetime.now(),
                next_check_time=datetime.now() + timedelta(hours=4),
                is_completed=False
            )
            db.session.add(reminder)
            db.session.commit()

            # 普通用户需要显示双重提示
            vip_upgrade_message = None
            if user.member_level == 'normal':
                vip_upgrade_message = '升级会员更实惠哦！等你啊  baby！'

            return {
                'action': 'wait',
                'message': '现在充值立即可用，或 4 小时后使用免费额度',
                'vip_upgrade_message': vip_upgrade_message,
                'next_check_time': reminder.next_check_time,
                'record_id': reminder.id,
                'annual_limit_reached': False
            }

        except Exception as e:
            db.session.rollback()
            print(f"❌ 处理普通用户/会员余额不足失败：{e}")
            return {
                'action': 'recharge',
                'message': '系统繁忙，请稍后再试',
                'error': str(e),
                'annual_limit_reached': False
            }

    def check_and_grant_registered_bonus(self, user):
        """
        检查并授予普通用户/会员 4 小时续赠额度

        触发条件：
        1. 用户类型为 registered 或 vip（会员未过期）
        2. 存在未完成的赠送记录
        3. 距离提醒时间已超过 4 小时
        4. 期间未充值（充值则取消赠送）
        5. 未达到年度上限
        6. 用户实际使用了产品（有消费记录）

        Args:
            user: 用户对象

        Returns:
            dict: {'success': bool, 'hairs': int, 'message': str, 'error': str}
        """
        try:
            # 检查年度上限
            bonus_count = self._get_registered_bonus_count_this_year(user)
            if bonus_count >= self.max_bonus_times_per_year:
                return {
                    'success': False,
                    'error': '本年度免费额度已用完',
                    'code': 'BONUS_EXHAUSTED'
                }

            # 查找待处理的赠送记录
            pending_records = UserBonusRecord.query.filter(
                UserBonusRecord.user_id == user.id,
                UserBonusRecord.is_completed == False,
                UserBonusRecord.next_check_time <= datetime.now()
            ).order_by(UserBonusRecord.reminded_at.desc()).limit(1).all()

            if not pending_records:
                return {
                    'success': False,
                    'error': '没有待处理的赠送记录',
                    'code': 'NO_PENDING_RECORD'
                }

            record = pending_records[0]

            # 检查期间是否充值（充值则取消赠送）
            recent_recharge = RechargeRecord.query.filter(
                RechargeRecord.user_id == user.id,
                RechargeRecord.payment_status == 'success',
                RechargeRecord.paid_at >= record.reminded_at
            ).first()

            if recent_recharge:
                # 期间已充值，取消赠送
                record.is_completed = True
                db.session.commit()
                return {
                    'success': False,
                    'error': '期间已充值，取消免费赠送',
                    'code': 'RECHARGED'
                }

            # 检查是否实际使用过产品（有消费记录）
            has_consumption = ConsumptionRecord.query.filter(
                ConsumptionRecord.user_id == user.id,
                ConsumptionRecord.status == 'success',
                ConsumptionRecord.created_at >= record.reminded_at
            ).first() is not None

            if not has_consumption:
                # 没有实际使用过产品，不赠送
                record.is_completed = True
                db.session.commit()
                return {
                    'success': False,
                    'error': '未检测到产品使用记录',
                    'code': 'NO_CONSUMPTION'
                }

            # 执行赠送
            bonus_hairs = record.hairs_added
            user.comb_hairs += bonus_hairs
            user.registered_bonus_used_count += 1
            user.last_registered_bonus_time = datetime.now()

            # 更新记录
            record.bonus_added_at = datetime.now()
            record.is_completed = True
            record.has_consumption_before_bonus = True

            db.session.commit()

            print(f"✅ 普通用户/会员 4 小时续赠头发丝：user_id={user.id}, "
                  f"user_type={user.member_level}, bonus={bonus_hairs}")

            return {
                'success': True,
                'hairs': bonus_hairs,
                'message': f'免费额度{bonus_hairs}根已到账'
            }

        except Exception as e:
            db.session.rollback()
            print(f"❌ 检查并授予普通用户/会员 4 小时续赠额度失败：{e}")
            return {
                'success': False,
                'error': str(e)
            }
