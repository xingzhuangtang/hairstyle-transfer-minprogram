#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信通知模块
支持两种模式：
1. Webhook 机器人（群消息）
2. 应用消息 API（指定用户）
"""

import json
import logging
import time
import requests

logger = logging.getLogger('self_healing')

SEVERITY_LABELS = {
    'critical': '🔴 严重',
    'high': '🟠 高危',
    'medium': '🟡 中危',
    'low': '🟢 低危',
}


class WeComBot:
    """企业微信通知机器人"""

    def __init__(self, webhook_url=None, corp_id=None, corp_secret=None, agent_id=None):
        self.webhook_url = webhook_url
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = int(agent_id) if agent_id else None

        self._access_token = None
        self._token_expires_at = 0
        self.session = requests.Session()
        self.session.timeout = 5

    def _get_access_token(self):
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        try:
            resp = self.session.get(
                'https://qyapi.weixin.qq.com/cgi-bin/gettoken',
                params={'corpid': self.corp_id, 'corpsecret': self.corp_secret},
                timeout=5,
            )
            data = resp.json()
            if data.get('errcode') == 0:
                self._access_token = data['access_token']
                self._token_expires_at = time.time() + data.get('expires_in', 7200) - 300
                return self._access_token
            else:
                logger.error(f'获取企业微信 access_token 失败: {data}')
                return None
        except Exception as e:
            logger.error(f'获取 access_token 异常: {e}')
            return None

    def _send_app_message(self, content, to_user='@all'):
        token = self._get_access_token()
        if not token:
            return False

        payload = {
            'touser': to_user,
            'msgtype': 'text',
            'agentid': self.agent_id,
            'text': {'content': content},
        }

        try:
            resp = self.session.post(
                f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}',
                json=payload,
                timeout=5,
            )
            result = resp.json()
            if result.get('errcode') == 0:
                logger.info(f'企业微信应用消息推送成功')
                return True
            else:
                logger.error(f'企业微信应用消息推送失败: {result}')
                return False
        except Exception as e:
            logger.error(f'企业微信应用消息推送异常: {e}')
            return False

    def _send_webhook(self, content):
        if not self.webhook_url:
            return False

        payload = {
            'msgtype': 'markdown',
            'markdown': {'content': content}
        }

        try:
            resp = self.session.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=5,
            )
            result = resp.json()
            if result.get('errcode') == 0:
                return True
            else:
                logger.error(f'企业微信 Webhook 推送失败: {result}')
                return False
        except Exception as e:
            logger.error(f'企业微信 Webhook 推送异常: {e}')
            return False

    def _send(self, markdown_content, text_content):
        if self.webhook_url:
            return self._send_webhook(markdown_content)
        elif self.corp_id and self.corp_secret and self.agent_id:
            return self._send_app_message(text_content)
        else:
            logger.debug('企业微信通知未配置，跳过')
            return False

    def send_alert(self, alert):
        severity = alert.get('severity', 'medium')
        title = alert.get('title', '未知告警')
        description = alert.get('description', '')
        source = alert.get('source_module', 'unknown')
        alert_id = alert.get('alert_id', 0)

        markdown_content = f"""## {SEVERITY_LABELS.get(severity, '⚪ 未知')} 系统告警

> **{title}**

**来源模块**: {source}
**告警ID**: {alert_id}

**详细描述**:
{description[:200] if description else '无'}

---
请及时登录开发者后台查看完整诊断报告并处理。"""

        text_content = f"""[{SEVERITY_LABELS.get(severity, '未知')} 系统告警]
{title}
来源模块: {source}
告警ID: {alert_id}
描述: {description[:200] if description else '无'}
请及时登录开发者后台查看完整诊断报告并处理。"""

        return self._send(markdown_content, text_content)

    def send_system_recovery(self, message):
        markdown_content = f"""## 🟢 系统恢复通知

> {message}

---
系统已恢复正常运行。"""

        text_content = f"[系统恢复] {message}"
        return self._send(markdown_content, text_content)
