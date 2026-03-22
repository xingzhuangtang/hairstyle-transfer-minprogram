#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会员服务模块
处理会员购买、到期提醒、自动降级等
"""

from datetime import datetime, timedelta
from models import db, User, MemberOrder, MemberReminder
from config import MEMBER_CONFIG


class MemberService:
    """会员服务"""
    
    def __init__(self):
        self.member_config = MEMBER_CONFIG
    
    def get_member_info(self, user):
        """
        获取会员信息
        
        Args:
            user: User对象
        
        Returns:
            dict: 会员信息
        """
        is_premium = user.is_premium()
        is_expired = user.is_member_expired()
        
        # 计算剩余天数
        remaining_days = 0
        if user.member_expire_at:
            if user.member_expire_at > datetime.now():
                remaining_days = (user.member_expire_at - datetime.now()).days
        
        return {
            'member_level': user.member_level,
            'is_premium': is_premium,
            'is_expired': is_expired,
            'expire_at': user.member_expire_at.isoformat() if user.member_expire_at else None,
            'remaining_days': remaining_days,
            'vip_config': self.member_config.get('vip', {})
        }
    
    def check_and_send_reminders(self):
        """
        检查并发送会员到期提醒
        定时任务：每天凌晨执行
        """
        try:
            now = datetime.now()
            
            # 查询所有陪跑会员
            premium_users = User.query.filter_by(member_level='premium').all()
            
            reminder_count = 0
            
            for user in premium_users:
                if not user.member_expire_at:
                    continue
                
                # 计算剩余天数
                remaining_days = (user.member_expire_at - now).days
                
                # 检查是否需要发送提醒
                reminder_type = None
                
                if remaining_days == 15:
                    reminder_type = '15days'
                elif remaining_days == 7:
                    reminder_type = '7days'
                elif remaining_days == 1:
                    reminder_type = '1day'
                
                if reminder_type:
                    # 检查是否已经发送过该类型的提醒
                    existing_reminder = MemberReminder.query.filter_by(
                        user_id=user.id,
                        member_expire_at=user.member_expire_at,
                        reminder_type=reminder_type
                    ).first()
                    
                    if not existing_reminder:
                        # 发送提醒
                        self._send_reminder(user, reminder_type, remaining_days)
                        
                        # 记录提醒
                        reminder = MemberReminder(
                            user_id=user.id,
                            member_expire_at=user.member_expire_at,
                            reminder_type=reminder_type,
                            status='sent'
                        )
                        db.session.add(reminder)
                        reminder_count += 1
            
            db.session.commit()
            
            if reminder_count > 0:
                print(f"✅ 会员到期提醒发送成功: {reminder_count}条")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 会员到期提醒检查失败: {e}")
            import traceback
            traceback.print_exc()
    
    def check_and_downgrade_expired_members(self):
        """
        检查并降级已过期会员
        定时任务：每小时执行
        """
        try:
            now = datetime.now()
            
            # 查询已过期的陪跑会员
            expired_users = User.query.filter(
                User.member_level == 'premium',
                User.member_expire_at.isnot(None),
                User.member_expire_at < now
            ).all()
            
            downgrade_count = 0
            
            for user in expired_users:
                # 降级为普通用户
                user.member_level = 'normal'
                user.member_expire_at = None
                
                # 发送降级通知
                self._send_downgrade_notification(user)
                
                downgrade_count += 1
            
            db.session.commit()
            
            if downgrade_count > 0:
                print(f"✅ 会员自动降级成功: {downgrade_count}个")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 会员自动降级检查失败: {e}")
            import traceback
            traceback.print_exc()
    
    def clean_expired_history_records(self):
        """
        清理过期历史记录
        定时任务：每天凌晨执行
        """
        try:
            now = datetime.now()
            
            # 查询已过期历史记录
            expired_records = HistoryRecord.query.filter(
                HistoryRecord.expire_at < now
            ).all()
            
            delete_count = len(expired_records)
            
            # 删除过期记录
            for record in expired_records:
                db.session.delete(record)
            
            db.session.commit()
            
            if delete_count > 0:
                print(f"✅ 过期历史记录清理成功: {delete_count}条")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 过期历史记录清理失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _send_reminder(self, user, reminder_type, remaining_days):
        """
        发送会员到期提醒
        
        Args:
            user: User对象
            reminder_type: 提醒类型
            remaining_days: 剩余天数
        """
        # TODO: 实现发送提醒（微信模板消息、短信等）
        print(f"📧 发送会员到期提醒: user_id={user.id}, "
              f"type={reminder_type}, days={remaining_days}")
    
    def _send_downgrade_notification(self, user):
        """
        发送会员降级通知
        
        Args:
            user: User对象
        """
        # TODO: 实现发送降级通知（微信模板消息、短信等）
        print(f"📧 发送会员降级通知: user_id={user.id}")
    
    def get_member_orders(self, user, page=1, page_size=20):
        """
        获取会员订单列表
        
        Args:
            user: User对象
            page: 页码
            page_size: 每页数量
        
        Returns:
            dict: {orders, total, page, page_size}
        """
        query = MemberOrder.query.filter_by(user_id=user.id).order_by(
            MemberOrder.created_at.desc()
        )
        
        total = query.count()
        orders = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            'orders': [o.to_dict() for o in orders],
            'total': total,
            'page': page,
            'page_size': page_size
        }


from models import HistoryRecord
