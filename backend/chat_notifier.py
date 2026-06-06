#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信聊天通知服务
用户发送聊天消息后，通过企业微信发送通知给管理员
"""

import os
import requests
from config import get_config


class ChatNotifier:
    """企业微信聊天通知"""

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

    def send_new_message_notification(self, user, message_content, reply_token):
        """
        发送新消息通知到企业微信

        Args:
            user: User 对象
            message_content: 用户发送的消息内容
            reply_token: 回复链接的 HMAC 签名 token

        Returns:
            bool: 是否发送成功
        """
        try:
            access_token = self._get_access_token()

            # 构建回复 URL
            reply_url = f"{self.base_url}/api/chat/reply?token={reply_token}"

            # 截取消息预览（最多100字符）
            preview = message_content[:100] + ("..." if len(message_content) > 100 else "")

            # 构建消息描述
            description = (
                f"用户: {user.nickname or '未命名用户'}\n"
                f"电话: {user.phone or '未绑定'}\n"
                f"会员: {'VIP' if user.member_level == 'vip' else '普通'}\n"
                f"消息: {preview}"
            )

            # 使用 template_card 消息类型，带跳转按钮
            message_content = {
                "touser": "@all",
                "msgtype": "template_card",
                "agentid": int(self.wechat_agent_id),
                "template_card": {
                    "card_type": "text_notice",
                    "main_title": {
                        "title": "新聊天消息",
                        "desc": f"{user.nickname or '用户'} 发来了一条消息"
                    },
                    "sub_title_text": description,
                    "jump_list": [
                        {
                            "type": 1,
                            "url": reply_url,
                            "title": "立即回复"
                        }
                    ],
                    "card_action": {
                        "type": 1,
                        "url": reply_url
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
                print(f"✅ 聊天通知已发送到企业微信")
                return True
            else:
                print(f"❌ 企业微信返回错误: {result}")
                return False

        except Exception as e:
            print(f"❌ 发送企业微信通知异常: {e}")
            return False

    def send_template_card(self, title, desc, description, reply_url):
        """
        发送自定义模板卡片通知到企业微信

        Args:
            title: 主标题
            desc: 副标题描述
            description: 详细内容
            reply_url: 跳转链接

        Returns:
            bool: 是否发送成功
        """
        try:
            access_token = self._get_access_token()

            message_content = {
                "touser": "@all",
                "msgtype": "template_card",
                "agentid": int(self.wechat_agent_id),
                "template_card": {
                    "card_type": "text_notice",
                    "main_title": {
                        "title": title,
                        "desc": desc
                    },
                    "sub_title_text": description,
                    "jump_list": [
                        {
                            "type": 1,
                            "url": reply_url,
                            "title": "立即回复"
                        }
                    ],
                    "card_action": {
                        "type": 1,
                        "url": reply_url
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
                print(f"✅ 模板卡片通知已发送到企业微信")
                return True
            else:
                print(f"❌ 企业微信返回错误: {result}")
                return False

        except Exception as e:
            print(f"❌ 发送企业微信模板卡片异常: {e}")
            return False
