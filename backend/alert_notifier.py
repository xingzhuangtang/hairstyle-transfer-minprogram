#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警通知系统
支持邮件、短信、微信等多渠道告警
"""

import os
import smtplib
import requests
import logging
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/hairstyle_alerts.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class AlertMessage:
    """告警消息"""

    title: str
    content: str
    severity: str  # info, warning, critical
    timestamp: datetime
    source: str
    metrics: Optional[Dict] = None


class AlertNotifier:
    """告警通知器"""

    def __init__(self):
        # 邮件配置
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.admin_emails = [
            email.strip()
            for email in os.getenv("ADMIN_EMAILS", "").split(",")
            if email.strip()
        ]

        # 短信配置（阿里云短信）
        self.sms_access_key_id = os.getenv("SMS_ACCESS_KEY_ID")
        self.sms_access_key_secret = os.getenv("SMS_ACCESS_KEY_SECRET")
        self.sms_sign_name = os.getenv("SMS_SIGN_NAME")
        self.admin_phones = [
            phone.strip()
            for phone in os.getenv("ADMIN_PHONES", "").split(",")
            if phone.strip()
        ]

        # 微信企业号配置
        self.wechat_corp_id = os.getenv("WECHAT_CORP_ID")
        self.wechat_corp_secret = os.getenv("WECHAT_CORP_SECRET")
        self.wechat_agent_id = os.getenv("WECHAT_AGENT_ID")

        # 钉钉机器人配置
        self.dingtalk_webhook = os.getenv("DINGTALK_WEBHOOK")

        # 告警缓存（避免重复告警）
        self.alert_cache = {}
        self.cache_expire_seconds = 3600  # 1小时内相同告警不重复发送

    def send_alert(self, alert: AlertMessage) -> bool:
        """发送告警（多渠道）"""
        try:
            # 检查是否重复告警
            alert_key = f"{alert.source}_{alert.title}"
            if self._is_duplicate_alert(alert_key):
                logger.info(f"跳过重复告警: {alert_key}")
                return True

            success_count = 0
            total_count = 0

            # 邮件告警
            if self.admin_emails and self._should_send_email(alert):
                total_count += 1
                if self._send_email_alert(alert):
                    success_count += 1
                    logger.info("邮件告警发送成功")
                else:
                    logger.error("邮件告警发送失败")

            # 短信告警（仅严重告警）
            if self.admin_phones and self._should_send_sms(alert):
                total_count += 1
                if self._send_sms_alert(alert):
                    success_count += 1
                    logger.info("短信告警发送成功")
                else:
                    logger.error("短信告警发送失败")

            # 微信告警
            if self.wechat_corp_id and self._should_send_wechat(alert):
                total_count += 1
                if self._send_wechat_alert(alert):
                    success_count += 1
                    logger.info("微信告警发送成功")
                else:
                    logger.error("微信告警发送失败")

            # 钉钉告警
            if self.dingtalk_webhook and self._should_send_dingtalk(alert):
                total_count += 1
                if self._send_dingtalk_alert(alert):
                    success_count += 1
                    logger.info("钉钉告警发送成功")
                else:
                    logger.error("钉钉告警发送失败")

            # 记录告警缓存
            self._record_alert(alert_key)

            if total_count == 0:
                logger.warning("没有配置告警渠道")
                return False

            # 至少一个渠道成功即为成功
            return success_count > 0

        except Exception as e:
            logger.error(f"发送告警失败: {str(e)}")
            return False

    def _send_email_alert(self, alert: AlertMessage) -> bool:
        """发送邮件告警"""
        try:
            if not self.smtp_user or not self.smtp_password or not self.admin_emails:
                return False

            # 构建邮件内容
            subject = f"[发型迁移系统] {alert.severity.upper()} - {alert.title}"

            # HTML邮件内容
            html_content = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ background-color: #f44336; color: white; padding: 10px; }}
                    .warning {{ background-color: #ff9800; color: white; padding: 10px; }}
                    .info {{ background-color: #2196F3; color: white; padding: 10px; }}
                    .content {{ padding: 20px; }}
                    .footer {{ background-color: #f5f5f5; padding: 10px; font-size: 12px; color: #666; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <div class="header {alert.severity}">
                    <h2>{alert.severity.upper()} - {alert.title}</h2>
                </div>
                <div class="content">
                    <p><strong>来源:</strong> {alert.source}</p>
                    <p><strong>时间:</strong> {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p><strong>内容:</strong></p>
                    <div style="background-color: #f9f9f9; padding: 10px; border-left: 4px solid #2196F3;">
                        {alert.content.replace("\n", "<br>")}
                    </div>
            """

            # 添加指标信息
            if alert.metrics:
                html_content += """
                    <p><strong>相关指标:</strong></p>
                    <table>
                """
                for key, value in alert.metrics.items():
                    html_content += f"<tr><td>{key}</td><td>{value}</td></tr>"
                html_content += "</table>"

            html_content += f"""
                </div>
                <div class="footer">
                    <p>此邮件由发型迁移系统自动发送，请勿回复。</p>
                    <p>如需配置告警，请联系系统管理员。</p>
                </div>
            </body>
            </html>
            """

            # 创建邮件
            msg = MimeMultipart("alternative")
            msg["From"] = self.smtp_user
            msg["To"] = ", ".join(self.admin_emails)
            msg["Subject"] = subject

            # 添加HTML内容
            html_part = MimeText(html_content, "html", "utf-8")
            msg.attach(html_part)

            # 发送邮件
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()

            return True

        except Exception as e:
            logger.error(f"发送邮件告警失败: {str(e)}")
            return False

    def _send_sms_alert(self, alert: AlertMessage) -> bool:
        """发送短信告警"""
        try:
            if not self.sms_access_key_id or not self.admin_phones:
                return False

            # 简化短信内容
            sms_content = f"[发型迁移系统]{alert.severity}:{alert.title} {alert.timestamp.strftime('%H:%M')}"

            # 这里应该调用阿里云短信API
            # 为了简化，这里只打印日志
            for phone in self.admin_phones:
                logger.info(f"模拟发送短信到 {phone}: {sms_content}")
                # 实际实现中调用:
                # from aliyunsdkcore.client import AcsClient
                # from aliyunsdkcore.request import CommonRequest
                # client = AcsClient(self.sms_access_key_id, self.sms_access_key_secret, 'cn-hangzhou')
                # request = CommonRequest()
                # request.set_accept_format('json')
                # request.set_domain('dysmsapi.aliyuncs.com')
                # request.set_method('POST')
                # request.set_version('2017-05-25')
                # request.set_action_name('SendSms')
                # request.add_query_param('PhoneNumbers', phone)
                # request.add_query_param('SignName', self.sms_sign_name)
                # request.add_query_param('TemplateCode', 'SMS_ALERT_TEMPLATE')
                # request.add_query_param('TemplateParam', json.dumps({'content': sms_content}))
                # response = client.do_action_with_exception(request)

            return True

        except Exception as e:
            logger.error(f"发送短信告警失败: {str(e)}")
            return False

    def _send_wechat_alert(self, alert: AlertMessage) -> bool:
        """发送微信企业号告警"""
        try:
            if not self.wechat_corp_id or not self.wechat_corp_secret:
                return False

            # 获取access_token
            token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.wechat_corp_id}&corpsecret={self.wechat_corp_secret}"
            response = requests.get(token_url, timeout=10)

            if response.status_code != 200:
                return False

            token_data = response.json()
            if token_data.get("errcode", 0) != 0:
                logger.error(f"获取微信access_token失败: {token_data}")
                return False

            access_token = token_data["access_token"]

            # 构建消息内容
            message_content = {
                "touser": "@all",  # 发送给所有人
                "msgtype": "textcard",
                "agentid": int(self.wechat_agent_id),
                "textcard": {
                    "title": f"[{alert.severity.upper()}] {alert.title}",
                    "description": f"""
来源: {alert.source}
时间: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

{alert.content}
                    """.strip(),
                    "url": "",  # 可以链接到监控面板
                    "btntxt": "查看详情",
                },
            }

            # 发送消息
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            response = requests.post(send_url, json=message_content, timeout=10)

            if response.status_code != 200:
                return False

            result = response.json()
            return result.get("errcode", 0) == 0

        except Exception as e:
            logger.error(f"发送微信告警失败: {str(e)}")
            return False

    def _send_dingtalk_alert(self, alert: AlertMessage) -> bool:
        """发送钉钉机器人告警"""
        try:
            if not self.dingtalk_webhook:
                return False

            # 构建消息内容
            color = (
                "#FF0000"
                if alert.severity == "critical"
                else "#FFA500"
                if alert.severity == "warning"
                else "#2196F3"
            )

            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"[{alert.severity.upper()}] {alert.title}",
                    "text": f"""
## <font color={color}>[{alert.severity.upper()}] {alert.title}</font>

**来源**: {alert.source}  
**时间**: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

**详情**:
{alert.content}

---
*发型迁移系统自动告警*
                    """,
                },
            }

            # 发送消息
            response = requests.post(self.dingtalk_webhook, json=message, timeout=10)

            if response.status_code != 200:
                return False

            result = response.json()
            return result.get("errcode", 0) == 0

        except Exception as e:
            logger.error(f"发送钉钉告警失败: {str(e)}")
            return False

    def _should_send_email(self, alert: AlertMessage) -> bool:
        """判断是否应该发送邮件告警"""
        return True  # 所有告警都发送邮件

    def _should_send_sms(self, alert: AlertMessage) -> bool:
        """判断是否应该发送短信告警"""
        return alert.severity in ["critical"]  # 只有严重告警发送短信

    def _should_send_wechat(self, alert: AlertMessage) -> bool:
        """判断是否应该发送微信告警"""
        return alert.severity in ["warning", "critical"]  # 警告和严重告警发送微信

    def _should_send_dingtalk(self, alert: AlertMessage) -> bool:
        """判断是否应该发送钉钉告警"""
        return alert.severity in ["warning", "critical"]  # 警告和严重告警发送钉钉

    def _is_duplicate_alert(self, alert_key: str) -> bool:
        """检查是否重复告警"""
        if alert_key not in self.alert_cache:
            return False

        last_sent = self.alert_cache[alert_key]
        return (datetime.now() - last_sent).seconds < self.cache_expire_seconds

    def _record_alert(self, alert_key: str):
        """记录告警时间"""
        self.alert_cache[alert_key] = datetime.now()

    def test_notifications(self) -> Dict[str, bool]:
        """测试所有通知渠道"""
        test_alert = AlertMessage(
            title="测试告警",
            content="这是一条测试告警消息，用于验证通知渠道是否正常工作。",
            severity="info",
            timestamp=datetime.now(),
            source="测试系统",
        )

        results = {}

        # 测试邮件
        if self.admin_emails:
            results["email"] = self._send_email_alert(test_alert)

        # 测试短信
        if self.admin_phones:
            results["sms"] = self._send_sms_alert(test_alert)

        # 测试微信
        if self.wechat_corp_id:
            results["wechat"] = self._send_wechat_alert(test_alert)

        # 测试钉钉
        if self.dingtalk_webhook:
            results["dingtalk"] = self._send_dingtalk_alert(test_alert)

        return results


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="告警通知系统")
    parser.add_argument("--test", action="store_true", help="测试告警通知")
    parser.add_argument("--title", type=str, help="告警标题")
    parser.add_argument("--content", type=str, help="告警内容")
    parser.add_argument(
        "--severity",
        type=str,
        choices=["info", "warning", "critical"],
        default="warning",
        help="告警级别",
    )
    parser.add_argument("--source", type=str, default="手动触发", help="告警来源")

    args = parser.parse_args()

    notifier = AlertNotifier()

    if args.test:
        logger.info("开始测试告警通知")
        results = notifier.test_notifications()

        print("告警测试结果:")
        for channel, success in results.items():
            status = "✓ 成功" if success else "✗ 失败"
            print(f"  {channel}: {status}")

    elif args.title and args.content:
        alert = AlertMessage(
            title=args.title,
            content=args.content,
            severity=args.severity,
            timestamp=datetime.now(),
            source=args.source,
        )

        success = notifier.send_alert(alert)
        if success:
            logger.info("告警发送成功")
        else:
            logger.error("告警发送失败")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
