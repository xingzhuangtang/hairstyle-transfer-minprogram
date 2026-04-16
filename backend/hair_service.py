#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
头发丝消费服务
处理头发丝扣除、消费记录等逻辑
"""

import uuid
from datetime import datetime, timedelta
from flask import g
from models import db, User, ConsumptionRecord, HistoryRecord
from config import PRICING_RULES, NORMAL_SERVICE_PRICING, VIP_SERVICE_PRICING


class HairService:
    """头发丝消费服务"""
    
    def __init__(self):
        self.pricing_rules = PRICING_RULES
    
    def get_pricing(self, user):
        """
        获取用户收费标准
        
        Args:
            user: User 对象
        
        Returns:
            dict: 收费标准
        """
        member_level = user.member_level
        
        # 检查会员是否过期
        if member_level == 'vip' and user.is_member_expired():
            member_level = 'normal'
        
        return self.pricing_rules.get(member_level, self.pricing_rules['normal'])
    
    def calculate_cost(self, user, service_type):
        """
        计算服务所需头发丝
        
        Args:
            user: User 对象
            service_type: 服务类型 (hair_segment, face_merge, sketch, combined)
        
        Returns:
            int: 所需头发丝数量
        """
        pricing = self.get_pricing(user)
        return pricing.get(service_type, 0)
    
    def consume_hairs(self, user, service_type, task_id=None, **kwargs):
        """
        消费头发丝
        
        Args:
            user: User 对象
            service_type: 服务类型
            task_id: 任务 ID（可选）
            **kwargs: 其他参数（result_url, sketch_url 等）
        
        Returns:
            dict: {success, error, scissor_deducted, comb_deducted, remaining_hairs}
        """
        try:
            # 生成任务 ID
            if not task_id:
                task_id = str(uuid.uuid4())
            
            # 计算所需头发丝
            required_hairs = self.calculate_cost(user, service_type)
            
            if required_hairs == 0:
                return {
                    'success': False,
                    'error': '服务类型错误'
                }
            
            # 检查头发丝是否足够
            if not user.has_enough_hairs(required_hairs):
                # 检查是否为游客
                if hasattr(user, 'user_type') and user.user_type == 'guest':
                    # 游客余额不足，走游客处理流程
                    from account_service import AccountService
                    account_service = AccountService()
                    guest_result = account_service.handle_guest_insufficient_balance(user, required_hairs)

                    if guest_result:
                        return {
                            'success': False,
                            'error': guest_result.get('message', '余额不足'),
                            'code': 'INSUFFICIENT_BALANCE',
                            'action': guest_result.get('action'),
                            'next_check_time': guest_result.get('next_check_time'),
                            'required': required_hairs,
                            'available': user.get_total_hairs()
                        }
                else:
                    # 普通用户/会员余额不足，走 4 小时赠送流程
                    from account_service import AccountService
                    account_service = AccountService()
                    registered_result = account_service.handle_registered_insufficient_balance(user, required_hairs)

                    if registered_result.get('annual_limit_reached'):
                        # 已达到年度上限
                        return {
                            'success': False,
                            'error': registered_result.get('message', '余额不足'),
                            'vip_upgrade_message': registered_result.get('vip_upgrade_message'),
                            'code': 'INSUFFICIENT_BALANCE',
                            'annual_limit_reached': True,
                            'required': required_hairs,
                            'available': user.get_total_hairs()
                        }
                    else:
                        # 未达上限，记录提醒时间，返回 4 小时后检查信息
                        return {
                            'success': False,
                            'error': registered_result.get('message', '余额不足'),
                            'vip_upgrade_message': registered_result.get('vip_upgrade_message'),
                            'code': 'INSUFFICIENT_BALANCE',
                            'next_check_time': registered_result.get('next_check_time'),
                            'required': required_hairs,
                            'available': user.get_total_hairs()
                        }
            
            # 扣除头发丝（优先从梳子卡槽扣除）
            comb_deducted = 0
            scissor_deducted = 0
            
            # 先从梳子卡槽扣除
            if user.comb_hairs >= required_hairs:
                comb_deducted = required_hairs
                user.comb_hairs -= required_hairs
            else:
                # 梳子卡槽不够，先扣完梳子卡槽
                comb_deducted = user.comb_hairs
                remaining = required_hairs - user.comb_hairs
                user.comb_hairs = 0
                
                # 再从剪刀卡槽扣除
                scissor_deducted = remaining
                user.scissor_hairs -= remaining
            
            # 更新累计消耗
            user.total_consumed_hairs += required_hairs
            
            # 保存用户信息
            db.session.commit()
            
            # 记录消费记录
            consumption_record = ConsumptionRecord(
                user_id=user.id,
                task_id=task_id,
                service_type=service_type,
                hairs_consumed=required_hairs,
                scissor_deducted=scissor_deducted,
                comb_deducted=comb_deducted,
                status='success',
                result_url=kwargs.get('result_url'),
                sketch_url=kwargs.get('sketch_url')
            )
            db.session.add(consumption_record)
            db.session.commit()
            
            # 如果是 vip 会员，保存历史记录
            if user.member_level == 'vip':
                self._save_history_record(user, task_id, service_type, **kwargs)
            
            print(f"✅ 头发丝消费成功：user_id={user.id}, service_type={service_type}, "
                  f"consumed={required_hairs}, comb={comb_deducted}, scissor={scissor_deducted}")
            
            return {
                'success': True,
                'task_id': task_id,
                'hairs_consumed': required_hairs,
                'scissor_deducted': scissor_deducted,
                'comb_deducted': comb_deducted,
                'remaining_scissor': user.scissor_hairs,
                'remaining_comb': user.comb_hairs,
                'remaining_total': user.get_total_hairs()
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 头发丝消费失败：{e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def refund_hairs(self, user, service_type, task_id, reason='服务失败'):
        """
        退还头发丝（服务失败时）
        
        Args:
            user: User 对象
            service_type: 服务类型
            task_id: 任务 ID
            reason: 退款原因
        
        Returns:
            dict: {success, error}
        """
        try:
            # 查找消费记录
            consumption = ConsumptionRecord.query.filter_by(
                user_id=user.id,
                task_id=task_id,
                service_type=service_type
            ).first()
            
            if not consumption:
                return {
                    'success': False,
                    'error': '消费记录不存在'
                }
            
            # 退还头发丝
            user.scissor_hairs += consumption.scissor_deducted
            user.comb_hairs += consumption.comb_deducted
            
            # 更新累计消耗
            user.total_consumed_hairs -= consumption.hairs_consumed
            
            # 更新消费记录状态
            consumption.status = 'failed'
            
            db.session.commit()
            
            print(f"✅ 头发丝退还成功：user_id={user.id}, task_id={task_id}, "
                  f"refunded={consumption.hairs_consumed}")
            
            return {
                'success': True,
                'refunded_hairs': consumption.hairs_consumed
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 头发丝退还失败：{e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_history_record(self, user, task_id, service_type, **kwargs):
        """
        保存历史记录（vip 会员专属）
        
        Args:
            user: User 对象
            task_id: 任务 ID
            service_type: 服务类型
            **kwargs: 其他参数
        """
        try:
            # 计算过期时间（45 天后）
            expire_at = datetime.now() + timedelta(days=45)
            
            # 创建历史记录
            history_record = HistoryRecord(
                user_id=user.id,
                task_id=task_id,
                service_type=service_type,
                original_hair_url=kwargs.get('original_hair_url'),
                customer_image_url=kwargs.get('customer_image_url'),
                result_url=kwargs.get('result_url'),
                sketch_url=kwargs.get('sketch_url'),
                model_version=kwargs.get('model_version'),
                face_blend_ratio=kwargs.get('face_blend_ratio'),
                expire_at=expire_at
            )
            
            db.session.add(history_record)
            db.session.commit()
            
            print(f"✅ 历史记录保存成功：user_id={user.id}, task_id={task_id}")
            
        except Exception as e:
            print(f"❌ 历史记录保存失败：{e}")
            # 不抛出异常，不影响主流程
    
    def get_user_balance(self, user):
        """
        获取用户余额信息
        
        Args:
            user: User 对象
        
        Returns:
            dict: 余额信息
        """
        return {
            'scissor_hairs': user.scissor_hairs,
            'comb_hairs': user.comb_hairs,
            'total_hairs': user.get_total_hairs(),
            'total_consumed': user.total_consumed_hairs,
            'total_recharge': float(user.total_recharge),
            'member_level': user.member_level,
            'is_vip': user.member_level == 'vip',
            'member_expire_at': user.member_expire_at.isoformat() if user.member_expire_at else None
        }
    
    def get_consumption_records(self, user, page=1, page_size=20):
        """
        获取用户消费记录
        
        Args:
            user: User 对象
            page: 页码
            page_size: 每页数量
        
        Returns:
            dict: {records, total, page, page_size}
        """
        query = ConsumptionRecord.query.filter_by(user_id=user.id).order_by(
            ConsumptionRecord.created_at.desc()
        )
        
        total = query.count()
        records = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            'records': [r.to_dict() for r in records],
            'total': total,
            'page': page,
            'page_size': page_size
        }
