#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推广返佣服务
处理推广二维码生成、扫码追踪、佣金发放、存钱罐管理、本地消费、提现等功能
"""

import os
import string
import random
import requests
from datetime import datetime
from decimal import Decimal

from models import db, User, ReferralRelation, CommissionRecord, CashWithdrawalRecord, CashConsumptionRecord, ConsumptionRecord
from config import get_config


class ReferralService:
    """推广返佣服务"""

    # 推广佣金金额（元）
    COMMISSION_AMOUNT = Decimal('0.03')
    # 解锁阈值（元）
    UNLOCK_THRESHOLD = Decimal('10.00')
    # 兑换比例：1元 = 100发丝
    EXCHANGE_RATE = 100
    # 小程序码宽度
    QRCODE_WIDTH = 430
    # 佣金发放封顶次数（每2次素描消费发一次，最多99次 = 198次素描消费）
    MAX_COMMISSION_TIMES = 99
    # 佣金冷却期：被推广人注册后24小时内的素描消费不计入佣金（防刷）
    COMMISSION_COOLDOWN_HOURS = 24

    def __init__(self):
        self.config = get_config()

    def _get_access_token(self):
        """获取微信小程序 access_token"""
        try:
            app_id = self.config.WECHAT_APP_ID
            app_secret = self.config.WECHAT_APP_SECRET
            if not app_id or not app_secret:
                print("❌ WECHAT_APP_ID 或 WECHAT_APP_SECRET 未配置")
                return None
            url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if 'access_token' in data:
                return data['access_token']
            else:
                print(f"❌ 获取access_token失败: {data}")
                return None
        except Exception as e:
            print(f"❌ 获取access_token异常: {e}")
            return None

    def generate_referral_code(self, user_id):
        """为用户生成唯一的推广码"""
        # 使用 base62 编码用户ID + 随机字符
        chars = string.ascii_letters + string.digits
        short_code = ''.join(random.choices(chars, k=8))
        return f"ref_{short_code}"

    def get_or_create_qrcode(self, user_id):
        """
        获取或创建用户的推广二维码
        使用微信 URL Link API + 本地 qrcode 库生成普通二维码
        返回: {success, qrcode_url, referral_code, error}
        """
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": "用户不存在"}

        # 如果已有推广码，检查是否有缓存的二维码URL
        if user.referral_code:
            # 已有推广码，直接返回（二维码URL在首次生成时已保存）
            if hasattr(user, 'qrcode_url') and user.qrcode_url:
                return {
                    "success": True,
                    "qrcode_url": user.qrcode_url,
                    "referral_code": user.referral_code,
                    "share_text": "分享二维码，朋友注册账户成功并使用两次素描效果功能，就能迎娶人民币回家"
                }

        else:
            user.referral_code = self.generate_referral_code(user_id)
            db.session.commit()

        scene = user.referral_code

        # 1. 调用微信 URL Link API 生成小程序链接
        try:
            access_token = self._get_access_token()
            if not access_token:
                return {"success": False, "error": "获取access_token失败"}

            # 生成 URL Link（跳转到首页并携带 scene 参数）
            urlink_url = f"https://api.weixin.qq.com/wxa/generate_urllink?access_token={access_token}"
            payload = {
                "path": "pages/index/index",
                "query": f"scene={scene}",
                "expire_type": 1,  # 永久有效
                "expire_interval": 0,
            }

            resp = requests.post(urlink_url, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if 'errcode' in data and data['errcode'] != 0:
                    # URL Link API 失败，降级为普通二维码
                    print(f"⚠️ URL Link API 失败: {data}，使用降级方案")
                    return self._generate_fallback_qrcode(user, scene)

                urllink = data.get('url_link', '')
                if not urllink:
                    return self._generate_fallback_qrcode(user, scene)

                # 2. 用 qrcode 库生成 URL Link 的二维码
                qr_image = self._generate_qr_image(urllink)
                if not qr_image:
                    return {"success": False, "error": "生成二维码图片失败"}

                # 3. 上传到 OSS
                import os
                from app import upload_to_oss
                upload_dir = "/tmp/qrcodes"
                os.makedirs(upload_dir, exist_ok=True)
                temp_path = os.path.join(upload_dir, f"qrcode_{user_id}_{scene}.png")
                qr_image.save(temp_path)

                oss_url = upload_to_oss(temp_path)
                if oss_url:
                    # 保存二维码 URL 到用户记录
                    try:
                        user.qrcode_url = oss_url
                        db.session.commit()
                    except Exception:
                        pass  # qrcode_url 字段可能尚未创建，忽略

                    return {
                        "success": True,
                        "qrcode_url": oss_url,
                        "referral_code": scene,
                        "share_text": "分享二维码，朋友注册账户成功并使用两次素描效果功能，就能迎娶人民币回家"
                    }
                else:
                    return {"success": False, "error": "二维码上传OSS失败"}
            else:
                return self._generate_fallback_qrcode(user, scene)

        except Exception as e:
            print(f"⚠️ URL Link 生成异常: {e}，使用降级方案")
            return self._generate_fallback_qrcode(user, scene)

    def _generate_fallback_qrcode(self, user, scene):
        """
        降级方案：生成普通二维码（内容为小程序跳转链接）
        """
        # 构造一个跳转 URL（需要前端在 app.js 中处理）
        redirect_url = f"https://xn--gmq63iba0780e.com/referral?scene={scene}"

        qr_image = self._generate_qr_image(redirect_url)
        if not qr_image:
            return {"success": False, "error": "生成二维码图片失败"}

        from app import upload_to_oss
        import os
        upload_dir = "/tmp/qrcodes"
        os.makedirs(upload_dir, exist_ok=True)
        temp_path = os.path.join(upload_dir, f"qrcode_{user.id}_{scene}_fallback.png")
        qr_image.save(temp_path)

        oss_url = upload_to_oss(temp_path)
        if oss_url:
            return {
                "success": True,
                "qrcode_url": oss_url,
                "referral_code": scene,
                "share_text": "分享二维码，朋友注册账户成功并使用两次素描效果功能，就能迎娶人民币回家"
            }
        return {"success": False, "error": "二维码上传OSS失败"}

    def _generate_qr_image(self, content, size=10):
        """使用 qrcode 库生成二维码图片"""
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=size,
                border=4,
            )
            qr.add_data(content)
            qr.make(fit=True)
            return qr.make_image(fill_color="black", back_color="white")
        except ImportError:
            # 如果没有 qrcode 库，尝试用 pillow 手动生成
            try:
                from PIL import Image, ImageDraw
                # 简单的黑白二维码
                img = Image.new('RGB', (400, 400), 'white')
                draw = ImageDraw.Draw(img)
                # 简单网格模拟（实际还是需要 qrcode 库）
                return None
            except ImportError:
                return None
        except Exception as e:
            print(f"❌ 生成二维码图片失败: {e}")
            return None

    def track_referral(self, user_id, scene):
        """
        追踪扫码来源，建立推广关系
        当新用户通过扫码进入小程序时调用
        """
        # 查找推广码对应的推广人
        referrer = User.query.filter_by(referral_code=scene).first()
        if not referrer:
            return {"success": False, "error": "推广码无效"}

        # 不能自己推广自己
        if referrer.id == user_id:
            return {"success": False, "error": "不能自己推广自己"}

        # 检查是否已有推广关系
        existing = ReferralRelation.query.filter_by(referee_id=user_id).first()
        if existing:
            return {"success": True, "message": "推广关系已存在", "referrer_id": existing.referrer_id}

        # 检查设备ID防刷
        user = User.query.get(user_id)
        if user and user.device_id:
            same_device = User.query.filter(
                User.device_id == user.device_id,
                User.id != user_id
            ).first()
            if same_device:
                return {"success": False, "error": "设备已存在，无法建立推广关系"}

        # 创建推广关系
        relation = ReferralRelation(
            referrer_id=referrer.id,
            referee_id=user_id,
            scene=scene,
            status='active'  # 用户已进入小程序，设为 active
        )
        db.session.add(relation)
        db.session.commit()

        return {
            "success": True,
            "referral_tracked": True,
            "referrer_id": referrer.id
        }

    def check_and_grant_commission(self, user_id):
        """
        检查并推广佣金发放
        被推广人每完成2次素描消费，给推广人发放 ¥0.03
        封顶 99 次（即被推广人最多 198 次素描消费触发佣金）
        在 hair_service.consume_hairs() 成功后调用
        """
        from datetime import timedelta

        # 查找该用户的推广关系
        relation = ReferralRelation.query.filter_by(
            referee_id=user_id
        ).first()

        if not relation:
            return  # 无推广关系

        # 检查是否已达 99 次封顶
        commission_count = CommissionRecord.query.filter_by(
            referral_id=relation.id,
            status='paid'
        ).count()

        if commission_count >= self.MAX_COMMISSION_TIMES:
            return  # 已达封顶，不再发放

        # 【防刷】检查冷却期：注册后24小时内的素描消费不计入佣金
        cooldown_end = relation.created_at + timedelta(hours=self.COMMISSION_COOLDOWN_HOURS)
        if datetime.now() < cooldown_end:
            remaining_hours = (cooldown_end - datetime.now()).total_seconds() / 3600
            print(f"⏳ 推广佣金冷却中：referee_id={user_id}, 剩余{remaining_hours:.1f}小时")
            return

        # 基于总素描消费次数计算应发佣金数（每2次消费发1次）
        # 只统计冷却期结束后的消费
        total_sketch_count = ConsumptionRecord.query.filter(
            ConsumptionRecord.user_id == user_id,
            ConsumptionRecord.service_type.in_(('sketch', 'combined')),
            ConsumptionRecord.status == 'success',
            ConsumptionRecord.created_at >= cooldown_end  # 只统计冷却期后的消费
        ).count()

        expected_commissions = total_sketch_count // 2

        # 只发放未发放过的佣金
        if expected_commissions > commission_count:
            # 发放佣金
            referrer = User.query.get(relation.referrer_id)
            if not referrer:
                return

            # 获取触发佣金的最近2次消费记录（用于来源追溯）
            recent_consumptions = ConsumptionRecord.query.filter(
                ConsumptionRecord.user_id == user_id,
                ConsumptionRecord.service_type.in_(('sketch', 'combined')),
                ConsumptionRecord.status == 'success',
                ConsumptionRecord.created_at >= cooldown_end
            ).order_by(ConsumptionRecord.created_at.desc()).limit(2).all()

            # 使用事务确保原子性
            try:
                referrer.cash_balance = (referrer.cash_balance or Decimal('0')) + self.COMMISSION_AMOUNT
                referrer.total_referral_earnings = (referrer.total_referral_earnings or Decimal('0')) + self.COMMISSION_AMOUNT
                referrer.referral_count = (referrer.referral_count or 0) + 1

                relation.commission_paid_at = datetime.now()

                # 创建佣金记录（带来源追溯信息）
                commission = CommissionRecord(
                    user_id=referrer.id,
                    referee_id=user_id,
                    referral_id=relation.id,
                    amount=self.COMMISSION_AMOUNT,
                    status='paid',
                    reason=f'好友 #{user_id} 完成素描消费 (共{total_sketch_count}次)'
                )
                db.session.add(commission)

                # 记录财务流水
                from financial_service import FinancialService
                FinancialService.record_commission(
                    user_id=referrer.id,
                    amount=float(self.COMMISSION_AMOUNT),
                    referee_id=user_id,
                    referral_id=relation.id,
                    status='success'
                )

                db.session.commit()

                print(f"✅ 推广佣金已发放：referrer_id={referrer.id}, referee_id={user_id}, "
                      f"amount={self.COMMISSION_AMOUNT}, 已发次数={commission_count + 1}/{self.MAX_COMMISSION_TIMES}")

            except Exception as e:
                db.session.rollback()
                print(f"⚠️ 推广佣金发放失败：{e}")

    def get_piggy_bank_stats(self, user_id):
        """
        获取存钱罐统计数据 + 佣金明细（带来源追溯）
        返回: {balance, local_consumption_unlocked, cash_withdrawal_unlocked, total_earnings, referral_count, commission_history}
        """
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": "用户不存在"}

        balance = user.cash_balance or Decimal('0')
        unlocked = balance >= self.UNLOCK_THRESHOLD

        # 获取佣金明细（带来源追溯）
        commission_records = CommissionRecord.query.filter_by(
            user_id=user_id,
            status='paid'
        ).order_by(CommissionRecord.created_at.desc()).all()

        commission_history = []
        for record in commission_records:
            # 查找被推广人信息
            referee = User.query.get(record.referee_id)
            commission_history.append({
                'amount': float(record.amount),
                'referee_id': record.referee_id,
                'referee_nickname': referee.nickname if referee else '未知用户',
                'reason': record.reason,
                'created_at': record.created_at.isoformat() if record.created_at else None
            })

        return {
            "success": True,
            "balance": float(balance),
            "local_consumption_unlocked": unlocked,
            "cash_withdrawal_unlocked": unlocked,
            "total_earnings": float(user.total_referral_earnings or Decimal('0')),
            "referral_count": user.referral_count or 0,
            "min_threshold": float(self.UNLOCK_THRESHOLD),
            "commission_history": commission_history  # 佣金明细（带来源追溯）
        }

    def consume_cash_for_hairs(self, user_id, amount):
        """
        本地消费：用现金余额购买发丝
        amount: 要消费的金额（元）
        """
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": "用户不存在"}

        balance = user.cash_balance or Decimal('0')
        amount = Decimal(str(amount))

        # 检查是否解锁
        if balance < self.UNLOCK_THRESHOLD:
            return {"success": False, "error": f"余额不足{self.UNLOCK_THRESHOLD}元，无法使用此功能"}

        # 检查余额
        if balance < amount:
            return {"success": False, "error": f"余额不足，当前余额：{float(balance)}元"}

        # 计算获得的发丝数量
        hairs_received = int(amount * self.EXCHANGE_RATE)

        try:
            # 扣除现金余额
            user.cash_balance = balance - amount
            # 增加发丝（放入梳子卡槽）
            user.comb_hairs += hairs_received

            # 创建消费记录
            record = CashConsumptionRecord(
                user_id=user_id,
                cash_spent=amount,
                hairs_received=hairs_received,
                exchange_rate=f"1元={self.EXCHANGE_RATE}发丝"
            )
            db.session.add(record)
            db.session.commit()

            # 记录财务流水
            from financial_service import FinancialService
            FinancialService.record_cash_consumption(
                user_id=user_id,
                cash_spent=float(amount),
                hairs_received=hairs_received,
                related_id=record.id
            )

            return {
                "success": True,
                "cash_spent": float(amount),
                "hairs_received": hairs_received,
                "remaining_balance": float(user.cash_balance)
            }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}

    def withdraw_cash(self, user_id, amount):
        """
        提现到微信零钱
        amount: 提现金额（元）
        """
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "error": "用户不存在"}

        if not user.openid:
            return {"success": False, "error": "请先绑定微信"}

        balance = user.cash_balance or Decimal('0')
        amount = Decimal(str(amount))

        # 检查是否解锁
        if balance < self.UNLOCK_THRESHOLD:
            return {"success": False, "error": f"余额不足{self.UNLOCK_THRESHOLD}元，无法提现"}

        # 检查余额
        if balance < amount:
            return {"success": False, "error": f"余额不足，当前余额：{float(balance)}元"}

        # 微信企业付款到零钱最低金额1元
        if amount < Decimal('1.00'):
            return {"success": False, "error": "最低提现金额为1元"}

        # 创建提现记录
        withdrawal = CashWithdrawalRecord(
            user_id=user_id,
            amount=amount,
            status='pending'
        )
        db.session.add(withdrawal)
        db.session.commit()

        # 调用微信企业付款
        try:
            from wechat_pay import WeChatPay
            wechat_pay = WeChatPay()

            # 生成商户订单号
            partner_trade_no = f"TX{int(datetime.now().timestamp() * 1000)}{user_id}"

            result = wechat_pay.enterprise_transfer(
                openid=user.openid,
                amount=float(amount),
                partner_trade_no=partner_trade_no,
                desc="发型迁移推广收益提现"
            )

            if result.get('success'):
                # 更新提现记录
                withdrawal.status = 'success'
                withdrawal.wechat_payment_no = result.get('payment_no', '')
                withdrawal.processed_at = datetime.now()

                # 扣除余额
                user.cash_balance = balance - amount

                # 记录财务流水
                from financial_service import FinancialService
                FinancialService.record_withdrawal(
                    user_id=user_id,
                    amount=float(amount),
                    withdrawal_id=withdrawal.id,
                    status='success'
                )

                db.session.commit()

                return {
                    "success": True,
                    "amount": float(amount),
                    "status": "success",
                    "message": "提现成功，已到账微信零钱"
                }
            else:
                withdrawal.status = 'failed'
                withdrawal.fail_reason = result.get('error', '提现失败')
                withdrawal.processed_at = datetime.now()
                db.session.commit()

                return {"success": False, "error": result.get('error', '提现失败')}

        except Exception as e:
            db.session.rollback()
            withdrawal.status = 'failed'
            withdrawal.fail_reason = str(e)
            withdrawal.processed_at = datetime.now()
            db.session.commit()

            return {"success": False, "error": f"提现处理失败：{str(e)}"}
