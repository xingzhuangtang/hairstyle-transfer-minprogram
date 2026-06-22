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

    def send_fix_result(self, fix_id, fix_name, status, result, alert_id=None):
        """发送修复结果通知"""
        status_icon = '✅' if status == 'success' else '❌'
        status_text = '成功' if status == 'success' else '失败'
        message = result.get('message', '') if isinstance(result, dict) else str(result)

        markdown_content = f"""## {status_icon} 自动修复{status_text}

> **{fix_name}**

**修复器**: {fix_id}
**告警ID**: {alert_id or '无'}
**结果**: {message[:200]}

---
自愈系统自动修复"""

        text_content = f"[自动修复{status_text}] {fix_name} | 告警ID:{alert_id or '无'} | {message[:100]}"
        return self._send(markdown_content, text_content)

    def send_approval_request(self, approval):
        """发送审批请求通知"""
        risk_labels = {'medium': '🟡 中危', 'high': '🔴 高危'}
        risk_text = risk_labels.get(approval.risk_level, approval.risk_level)

        markdown_content = f"""## 📋 待审批修复

> **{approval.fix_name}**

**风险级别**: {risk_text}
**修复ID**: {approval.fix_id}
**告警ID**: {approval.alert_id}

**修复方案**:
{approval.fix_description or '无'}

---
请登录开发者后台审批"""

        text_content = f"[待审批] {approval.fix_name} | 风险:{approval.risk_level} | 告警ID:{approval.alert_id} | 请登录后台审批"
        return self._send(markdown_content, text_content)

    def send_evolution_report(self, report):
        """发送进化报告通知"""
        health = report.get('health', {})
        score = health.get('score', 0)
        level = health.get('level', 'unknown')
        risks = report.get('risks', {})
        risk_count = len(risks.get('risks', []))

        level_labels = {
            'excellent': '优秀',
            'good': '良好',
            'warning': '警告',
            'critical': '危险',
        }

        markdown_content = f"""## 📊 系统进化报告

> **健康评分: {score}/100 ({level_labels.get(level, level)})**

**评分明细**:
- 告警频率: {health.get('breakdown', {}).get('alert_score', 0)}
- 修复成功率: {health.get('breakdown', {}).get('fix_score', 0)}
- 系统指标: {health.get('breakdown', {}).get('system_score', 0)}
- 防御覆盖率: {health.get('breakdown', {}).get('defense_score', 0)}

**风险预警**: {risk_count} 项

---
自愈系统进化分析"""

        top_risks = risks.get('risks', [])[:3]
        risk_text = '; '.join(r.get('message', '')[:50] for r in top_risks)
        text_content = f"[进化报告] 健康评分:{score}/100({level_labels.get(level, level)}) | 风险:{risk_count}项 | {risk_text}"
        return self._send(markdown_content, text_content)
