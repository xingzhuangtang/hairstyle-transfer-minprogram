#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务模块
使用Celery处理定时任务
"""

from celery import Celery
from celery.schedules import crontab
from config import get_config
from member_service import MemberService


# 创建Celery应用
def make_celery(app):
    """创建Celery实例"""
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
    
    # 每天凌晨2点检查会员到期提醒
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
    
    # 每天凌晨3点清理过期历史记录
    @celery.task
    def clean_history_records():
        """清理过期历史记录"""
        with app.app_context():
            member_service = MemberService()
            member_service.clean_expired_history_records()
    
    # 配置定时任务
    celery.conf.beat_schedule = {
        # 每天凌晨2点检查会员到期提醒
        'check-member-reminders': {
            'task': 'scheduler.check_member_reminders',
            'schedule': crontab(hour=2, minute=0),
        },
        # 每小时检查会员自动降级
        'check-member-downgrade': {
            'task': 'scheduler.check_member_downgrade',
            'schedule': crontab(minute=0),
        },
        # 每天凌晨3点清理过期历史记录
        'clean-history-records': {
            'task': 'scheduler.clean_history_records',
            'schedule': crontab(hour=3, minute=0),
        },
    }
    
    return celery


# 启动Celery Beat
if __name__ == '__main__':
    from app import create_app
    
    app = create_app()
    celery = make_celery(app)
    celery = configure_scheduler(celery, app)
    
    # 启动Celery Beat
    celery.start()
