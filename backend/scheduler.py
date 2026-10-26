#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务模块
使用 Celery 处理定时任务
"""

from celery import Celery
from celery.schedules import crontab
from config import get_config
from member_service import MemberService


# 创建 Celery 应用
def make_celery(app):
    """创建 Celery 实例"""
    config = get_config()

    celery = Celery(
        app.import_name,
        broker=f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}",
        backend=f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"
    )

    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Shanghai',
        enable_utc=True,
    )

    return celery


# 定时任务配置
def configure_scheduler(celery, app):
    """配置定时任务"""

    # 每天凌晨 2 点检查会员到期提醒
    @celery.task
    def check_member_reminders():
        """检查会员到期提醒"""
        with app.app_context():
            member_service = MemberService()
            member_service.check_and_send_reminders()

    # 每小时检查会员自动降级
    @celery.task
    def check_member_downgrade():
        """检查会员自动降级"""
        with app.app_context():
            member_service = MemberService()
            member_service.check_and_downgrade_expired_members()

    # 每天凌晨 3 点清理过期历史记录
    @celery.task
    def clean_history_records():
        """清理过期历史记录"""
        with app.app_context():
            member_service = MemberService()
            member_service.clean_expired_history_records()

    # 每 30 分钟检查游客 4 小时续赠额度
    @celery.task
    def check_guest_bonus():
        """检查并发放游客 4 小时续赠额度"""
        with app.app_context():
            from account_service import AccountService
            from models import GuestBonusRecord, User
            from datetime import datetime

            # 查找待处理的赠送记录
            pending_records = GuestBonusRecord.query.filter(
                GuestBonusRecord.bonus_type == 'auto_renew',
                GuestBonusRecord.is_completed == False,
                GuestBonusRecord.next_check_time <= datetime.now()
            ).all()

            account_service = AccountService()
            success_count = 0
            skip_count = 0

            for record in pending_records:
                user = User.query.get(record.user_id)
                if not user:
                    continue

                result = account_service.check_and_grant_guest_bonus(user)

                if result['success']:
                    success_count += 1
                    print(f"✅ 游客续赠发放成功：user_id={user.id}, openid={user.openid}, "
                          f"hairs={result['hairs']}")
                else:
                    skip_count += 1
                    print(f"ℹ️ 游客续赠跳过：user_id={user.id}, reason={result.get('error')}")

            if success_count > 0:
                print(f"✅ 本次检查共发放 {success_count} 笔游客续赠，跳过 {skip_count} 笔")

    # 每 30 分钟检查普通用户/会员 4 小时续赠额度
    @celery.task
    def check_registered_bonus():
        """检查并发放普通用户/会员 4 小时续赠额度"""
        with app.app_context():
            from account_service import AccountService
            from models import UserBonusRecord, User
            from datetime import datetime

            # 查找待处理的赠送记录
            pending_records = UserBonusRecord.query.filter(
                UserBonusRecord.is_completed == False,
                UserBonusRecord.next_check_time <= datetime.now()
            ).all()

            account_service = AccountService()
            success_count = 0
            skip_count = 0

            for record in pending_records:
                user = User.query.get(record.user_id)
                if not user:
                    continue

                result = account_service.check_and_grant_registered_bonus(user)

                if result['success']:
                    success_count += 1
                    print(f"✅ 普通用户/会员续赠发放成功：user_id={user.id}, "
                          f"user_type={user.member_level}, hairs={result['hairs']}")
                else:
                    skip_count += 1
                    print(f"ℹ️ 普通用户/会员续赠跳过：user_id={user.id}, "
                          f"reason={result.get('error')}")

            if success_count > 0:
                print(f"✅ 本次检查共发放 {success_count} 笔普通用户/会员续赠，跳过 {skip_count} 笔")

    # 每 5 分钟检查待支付订单（补偿回调丢失）
    @celery.task
    def check_pending_recharge_orders():
        """检查待支付订单，主动查询微信支付状态"""
        with app.app_context():
            from models import RechargeRecord, MemberOrder, db
            from payment_service import PaymentService, WeChatPayService
            from datetime import datetime, timedelta

            # 查找2分钟前创建的待支付订单（给回调一些时间）
            cutoff_time = datetime.now() - timedelta(minutes=2)

            pending_recharge_orders = RechargeRecord.query.filter(
                RechargeRecord.payment_status == 'pending',
                RechargeRecord.created_at <= cutoff_time
            ).all()

            pending_member_orders = MemberOrder.query.filter(
                MemberOrder.payment_status == 'pending',
                MemberOrder.created_at <= cutoff_time
            ).all()

            if not pending_recharge_orders and not pending_member_orders:
                return

            payment_service = PaymentService()
            fixed_count = 0
            queried_count = 0

            # 检查充值订单
            for order in pending_recharge_orders:
                try:
                    time_diff = datetime.now() - order.created_at

                    # 对于普通微信支付订单，主动查询微信 API
                    if order.payment_method == 'wechat' and time_diff > timedelta(minutes=2):
                        try:
                            wechat_service = WeChatPayService()
                            result = wechat_service.wechat_pay.query_order(order.order_no)

                            if result.get('success'):
                                trade_state = result.get('trade_state')
                                queried_count += 1

                                if trade_state == 'SUCCESS':
                                    # 支付成功，处理订单
                                    transaction_id = result.get('transaction_id', f"QUERY_{order.order_no}")
                                    process_result = payment_service.process_recharge_success(
                                        order.order_no, transaction_id
                                    )
                                    if process_result['success']:
                                        print(f"✅ 补偿成功（微信查询）: {order.order_no}")
                                        fixed_count += 1
                                    else:
                                        print(f"❌ 补偿处理失败: {order.order_no}, error={process_result.get('error')}")
                                elif trade_state in ['CLOSED', 'REVOKED', 'PAYERROR']:
                                    # 支付失败或关闭
                                    order.payment_status = 'failed'
                                    print(f"⚠️ 订单支付失败: {order.order_no}, state={trade_state}")
                                    fixed_count += 1
                                # else: 仍在支付中，不处理
                        except Exception as e:
                            print(f"❌ 查询微信支付订单失败 {order.order_no}: {e}")

                    # 对于虚拟支付订单，暂时无法主动查询，延长超时时间到 60 分钟
                    elif order.payment_method == 'wechat_virtual':
                        if time_diff > timedelta(minutes=60):
                            order.payment_status = 'failed'
                            print(f"️ 虚拟支付订单超时自动关闭: {order.order_no}")
                            fixed_count += 1

                    # 其他支付方式，30 分钟超时
                    else:
                        if time_diff > timedelta(minutes=30):
                            order.payment_status = 'failed'
                            print(f"️ 订单超时自动关闭: {order.order_no}")
                            fixed_count += 1

                except Exception as e:
                    print(f"❌ 检查订单失败 {order.order_no}: {e}")

            # 检查会员订单
            for order in pending_member_orders:
                try:
                    time_diff = datetime.now() - order.created_at

                    # 对于普通微信支付订单，主动查询
                    if order.payment_method == 'wechat' and time_diff > timedelta(minutes=2):
                        try:
                            wechat_service = WeChatPayService()
                            result = wechat_service.wechat_pay.query_order(order.order_no)

                            if result.get('success'):
                                trade_state = result.get('trade_state')
                                queried_count += 1

                                if trade_state == 'SUCCESS':
                                    transaction_id = result.get('transaction_id', f"QUERY_{order.order_no}")
                                    process_result = payment_service.process_member_success(
                                        order.order_no, transaction_id
                                    )
                                    if process_result['success']:
                                        print(f"✅ 会员订单补偿成功（微信查询）: {order.order_no}")
                                        fixed_count += 1
                                    else:
                                        print(f"❌ 会员订单补偿处理失败: {order.order_no}, error={process_result.get('error')}")
                                elif trade_state in ['CLOSED', 'REVOKED', 'PAYERROR']:
                                    order.payment_status = 'failed'
                                    print(f"⚠️ 会员订单支付失败: {order.order_no}, state={trade_state}")
                                    fixed_count += 1
                        except Exception as e:
                            print(f"❌ 查询微信会员订单失败 {order.order_no}: {e}")

                    # 虚拟支付订单，60 分钟超时
                    elif order.payment_method == 'wechat_virtual':
                        if time_diff > timedelta(minutes=60):
                            order.payment_status = 'failed'
                            print(f"⚠️ 虚拟支付会员订单超时自动关闭: {order.order_no}")
                            fixed_count += 1

                    # 其他支付方式，30 分钟超时
                    else:
                        if time_diff > timedelta(minutes=30):
                            order.payment_status = 'failed'
                            print(f"⚠️ 会员订单超时自动关闭: {order.order_no}")
                            fixed_count += 1

                except Exception as e:
                    print(f" 检查会员订单失败 {order.order_no}: {e}")

            if fixed_count > 0 or queried_count > 0:
                db.session.commit()
                print(f"✅ 本次检查共处理 {fixed_count} 个订单，查询 {queried_count} 个微信订单")

    # 配置定时任务
    celery.conf.beat_schedule = {
        # 每天凌晨 2 点检查会员到期提醒
        'check-member-reminders': {
            'task': 'scheduler.check_member_reminders',
            'schedule': crontab(hour=2, minute=0),
        },
        # 每小时检查会员自动降级
        'check-member-downgrade': {
            'task': 'scheduler.check_member_downgrade',
            'schedule': crontab(minute=0),
        },
        # 每天凌晨 3 点清理过期历史记录
        'clean-history-records': {
            'task': 'scheduler.clean_history_records',
            'schedule': crontab(hour=3, minute=0),
        },
        # 每 30 分钟检查游客 4 小时续赠额度
        'check-guest-bonus': {
            'task': 'scheduler.check_guest_bonus',
            'schedule': crontab(minute='*/30'),
        },
        # 每 30 分钟检查普通用户/会员 4 小时续赠额度
        'check-registered-bonus': {
            'task': 'scheduler.check_registered_bonus',
            'schedule': crontab(minute='*/30'),
        },
        # 每 5 分钟检查待支付订单（补偿回调丢失）
        'check-pending-recharge-orders': {
            'task': 'scheduler.check_pending_recharge_orders',
            'schedule': crontab(minute='*/5'),
        },
    }

    return celery


# 启动 Celery Beat
if __name__ == '__main__':
    from app import create_app

    app = create_app()
    celery = make_celery(app)
    celery = configure_scheduler(celery, app)

    # 启动 Celery Beat
    celery.start()
