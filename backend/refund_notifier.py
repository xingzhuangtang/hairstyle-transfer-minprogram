#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信退款通知服务
退款申请提交后，通过企业微信发送审批通知给管理员
"""

import os
import requests
from config import get_config


class RefundNotifier:
    """企业微信退款通知"""

    def __init__(self):
        self.config = get_config()
        self.wechat_corp_id = self.config.WECHAT_CORP_ID
        self.wechat_corp_secret = self.config.WECHAT_CORP_SECRET
        self.wechat_agent_id = self.config.WECHAT_AGENT_ID
        self.base_url = os.getenv("SERVER_URL", "https://xn--gmq63iba0780e.com")

    def _get_access_token(self):
        """获取企业微信 access_token"""
        if not self.wechat_corp_id or not self.wechat_corp_secret:
            raise Exception("企业微信配置不完整")

        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.wechat_corp_id}&corpsecret={self.wechat_corp_secret}"
        response = requests.get(token_url, timeout=10)

        if response.status_code != 200:
            raise Exception(f"获取 access_token 失败: HTTP {response.status_code}")

        token_data = response.json()
        if token_data.get("errcode", 0) != 0:
            raise Exception(f"获取 access_token 失败: {token_data}")

        return token_data["access_token"]

    def send_refund_application_notification(self, application, approval_token):
        """
        发送退款申请通知到企业微信

        Args:
            application: RefundApplication 对象
            approval_token: 审批链接的 HMAC 签名 token

        Returns:
            bool: 是否发送成功
        """
        try:
            access_token = self._get_access_token()

            # 构建审批 URL
            approval_url = f"{self.base_url}/api/refund/approve?token={approval_token}"

            # 构建消息内容
            refund_type_text = "充值退款" if application.refund_type == 'recharge' else "会员退款"
            summary = application.consumption_summary or {}

            description = (
                f"申请人: {application.applicant_name}\n"
                f"电话: {application.applicant_phone}\n"
                f"微信号: {application.applicant_wechat_id or '未填写'}\n"
                f"退款类型: {refund_type_text}\n"
                f"退款金额: ¥{application.refund_amount}\n"
                f"申请原因: {application.reason[:100]}\n"
                f"{'累计充值: ¥' + str(summary.get('total_spent', 0)) if summary.get('total_spent') else ''}\n"
                f"{'剩余发丝: ' + str(summary.get('remaining_hairs', 0)) if summary.get('remaining_hairs') is not None else ''}"
            ).strip()

            # 使用 template_card 消息类型，带跳转按钮
            message_content = {
                "touser": "@all",
                "msgtype": "template_card",
                "agentid": int(self.wechat_agent_id),
                "template_card": {
                    "card_type": "text_notice",
                    "main_title": {
                        "title": "退款申请待审批",
                        "desc": f"{application.applicant_name} 申请{refund_type_text} ¥{application.refund_amount}"
                    },
                    "sub_title_text": description,
                    "jump_list": [
                        {
                            "type": 1,
                            "url": f"{approval_url}&action=approve",
                            "title": "同意退款"
                        },
                        {
                            "type": 1,
                            "url": f"{approval_url}&action=reject",
                            "title": "拒绝退款"
                        }
                    ],
                    "card_action": {
                        "type": 1,
                        "url": f"{approval_url}&action=approve"
                    }
                }
            }

            # 发送消息
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            response = requests.post(send_url, json=message_content, timeout=10)

            if response.status_code != 200:
                print(f"❌ 企业微信消息发送失败: HTTP {response.status_code}")
                return False

            result = response.json()
            if result.get("errcode", -1) == 0:
                print(f"✅ 退款申请通知已发送到企业微信")
                return True
            else:
                print(f"❌ 企业微信返回错误: {result}")
                return False

        except Exception as e:
            print(f"❌ 发送企业微信通知异常: {e}")
            return False

    def send_calculation_preview_notification(self, user, calculation):
        """
        客户查看核算清单时，发送预览通知到企业微信
        
        Args:
            user: User 对象
            calculation: 核算清单数据
            
        Returns:
            bool: 是否发送成功
        """
        try:
            access_token = self._get_access_token()
            
            refund_type_text = "充值退款" if calculation.get('refund_type') == 'recharge' else "会员退款"
            
            # 构建核算清单内容
            if calculation.get('refund_type') == 'recharge':
                detail = (
                    f"充值金额: ¥{calculation.get('charge_amount', 0)}\n"
                    f"获得发丝: {calculation.get('charge_hairs', 0)}\n"
                    f"申请退款: ¥{calculation.get('refund_amount_requested', 0)}\n"
                    f"应扣回发丝: {calculation.get('hairs_to_deduct', 0)}\n"
                    f"剩余发丝: {calculation.get('total_hairs', 0)}"
                )
            else:
                detail = (
                    f"会员价格: ¥{calculation.get('member_price', 99)}\n"
                    f"剩余天数: {calculation.get('remaining_days', 0)}天\n"
                    f"应退金额: ¥{calculation.get('refund_amount_requested', 0)}\n"
                    f"应扣回发丝: {calculation.get('hairs_to_deduct', 0)}\n"
                    f"剩余发丝: {calculation.get('total_hairs', 0)}"
                )
            
            # 核算结果
            if calculation.get('hairs_sufficient'):
                result_text = f"✅ 最终退款: ¥{calculation.get('actual_refund', 0)}"
            else:
                missing = calculation.get('missing_hairs', 0)
                cash_deduction = calculation.get('cash_deduction', 0)
                result_text = (
                    f"⚠️ 发丝不足 {missing} 根\n"
                    f"现金抵扣: ¥{cash_deduction}\n"
                    f"最终退款: ¥{calculation.get('actual_refund', 0)}"
                )
            
            description = (
                f"客户: {user.nickname or '未设置'} ({user.phone or '未绑定'})\n"
                f"退款类型: {refund_type_text}\n"
                f"---\n"
                f"{detail}\n"
                f"---\n"
                f"{result_text}"
            )
            
            message_content = {
                "touser": "@all",
                "msgtype": "text",
                "agentid": int(self.wechat_agent_id),
                "text": {
                    "content": f" 客户查看退款核算清单\n\n客户: {user.nickname or '未设置'} ({user.phone or '未绑定'})\n退款类型: {refund_type_text}\n---\n{detail}\n---\n{result_text}"
                }
            }
            
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            response = requests.post(send_url, json=message_content, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ 核算清单通知发送失败: HTTP {response.status_code}")
                return False
            
            result = response.json()
            if result.get("errcode", -1) == 0:
                print(f"✅ 核算清单预览通知已发送到企业微信")
                return True
            else:
                print(f"❌ 企业微信返回错误: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 发送核算清单通知异常: {e}")
            return False

    def send_approval_notification_with_calculation(self, application, approval_token, calculation=None):
        """
        发送带核算清单的审批通知
        
        Args:
            application: RefundApplication 对象
            approval_token: 审批链接的 HMAC 签名 token
            calculation: 核算清单数据（可选）
            
        Returns:
            bool: 是否发送成功
        """
        try:
            access_token = self._get_access_token()
            approval_url = f"{self.base_url}/api/refund/approve?token={approval_token}"
            
            refund_type_text = "充值退款" if application.refund_type == 'recharge' else "会员退款"
            summary = application.consumption_summary or {}
            
            # 基础信息
            description = (
                f"申请人: {application.applicant_name}\n"
                f"电话: {application.applicant_phone}\n"
                f"退款类型: {refund_type_text}\n"
                f"申请金额: ¥{application.refund_amount}\n"
                f"申请原因: {application.reason[:100]}"
            )
            
            # 如果有核算清单，添加到描述中
            if calculation:
                calc_text = "\n--- 核算清单 ---\n"
                if calculation.get('refund_type') == 'recharge':
                    calc_text += f"充值金额: ¥{calculation.get('charge_amount', 0)}\n"
                    calc_text += f"获得发丝: {calculation.get('charge_hairs', 0)}\n"
                else:
                    calc_text += f"会员价格: ¥{calculation.get('member_price', 99)}\n"
                    calc_text += f"剩余天数: {calculation.get('remaining_days', 0)}天\n"
                
                calc_text += f"应扣回发丝: {calculation.get('hairs_to_deduct', 0)}\n"
                calc_text += f"剩余发丝: {calculation.get('total_hairs', 0)}\n"
                
                if calculation.get('hairs_sufficient'):
                    calc_text += f"✅ 最终退款: ¥{calculation.get('actual_refund', 0)}"
                else:
                    calc_text += f"⚠️ 差额: {calculation.get('missing_hairs', 0)}发丝\n"
                    calc_text += f"现金抵扣: ¥{calculation.get('cash_deduction', 0)}\n"
                    calc_text += f"最终退款: ¥{calculation.get('actual_refund', 0)}"
                
                description += calc_text
            
            message_content = {
                "touser": "@all",
                "msgtype": "template_card",
                "agentid": int(self.wechat_agent_id),
                "template_card": {
                    "card_type": "text_notice",
                    "main_title": {
                        "title": "退款申请待审批",
                        "desc": f"{application.applicant_name} 申请{refund_type_text} ¥{application.refund_amount}"
                    },
                    "sub_title_text": description,
                    "jump_list": [
                        {
                            "type": 1,
                            "url": f"{approval_url}&action=approve",
                            "title": "同意退款"
                        },
                        {
                            "type": 1,
                            "url": f"{approval_url}&action=reject",
                            "title": "拒绝退款"
                        }
                    ],
                    "card_action": {
                        "type": 1,
                        "url": f"{approval_url}&action=approve"
                    }
                }
            }
            
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            response = requests.post(send_url, json=message_content, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ 企业微信消息发送失败: HTTP {response.status_code}")
                return False
            
            result = response.json()
            if result.get("errcode", -1) == 0:
                print(f"✅ 退款审批通知（含核算清单）已发送到企业微信")
                return True
            else:
                print(f"❌ 企业微信返回错误: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 发送企业微信通知异常: {e}")
            return False
