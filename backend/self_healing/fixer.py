#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动修复引擎
预定义修复脚本库，按风险级别自动执行或走审批流
"""

import gc
import json
import logging
import os
import re
import threading
import time
from datetime import datetime

logger = logging.getLogger('self_healing')


class AutoFixer:
    """自动修复引擎"""

    def __init__(self, app, config, db=None, redis_client=None, wecom_bot=None):
        self.app = app
        self.config = config
        self.db = db
        self.redis = redis_client
        self.wecom_bot = wecom_bot
        self._approval_manager = None
        self._lock = threading.Lock()

    def set_approval_manager(self, approval_manager):
        self._approval_manager = approval_manager

    def get_fix_registry(self):
        """返回可用修复器列表"""
        return [
            {
                'id': 'redis_recovery',
                'name': 'Redis 连接恢复',
                'description': '检测 Redis 连接状态，重建连接',
                'risk': 'low',
                'match_keywords': ['Redis', 'redis', 'redis.exceptions', 'ConnectionError'],
            },
            {
                'id': 'db_reconnect',
                'name': '数据库连接恢复',
                'description': '检测数据库连接状态，触发连接池重建',
                'risk': 'low',
                'match_keywords': ['OperationalError', 'MySQL', 'pymysql', 'LostConnection', 'database is down', 'database down'],
            },
            {
                'id': 'memory_relief',
                'name': '内存清理',
                'description': '执行垃圾回收，清理内部缓存',
                'risk': 'medium',
                'match_keywords': ['MemoryError', 'memory', '内存', 'OOM'],
            },
            {
                'id': 'disk_cleanup',
                'name': '磁盘清理',
                'description': '清理临时文件和过期日志',
                'risk': 'medium',
                'match_keywords': ['disk', 'Disk', 'No space', '磁盘', 'storage'],
            },
            {
                'id': 'slow_query_kill',
                'name': '慢查询清理',
                'description': '检测并清理长时间运行的数据库查询',
                'risk': 'high',
                'match_keywords': ['slow query', 'lock wait', 'Lock wait', 'timeout', 'deadlock'],
            },
            {
                'id': 'domain_config_check',
                'name': '域名配置检查',
                'description': '检查回调地址等关键域名配置是否可达，发现不可达域名时发送告警',
                'risk': 'low',
                'match_keywords': ['域名', 'domain', 'DNS', '回调', 'callback', '无法解析', 'NOTIFY_URL'],
            },
        ]

    def try_auto_fix(self, alert_id):
        """尝试自动修复（由 alert_manager 在告警后调用）"""
        try:
            with self.app.app_context():
                alert = self._get_alert(alert_id)
                if not alert:
                    return

                registry = self.get_fix_registry()
                matched = self._match_fixer(alert, registry)

                if not matched:
                    return

                fixer = matched
                risk = fixer['risk']

                if risk == 'low':
                    self._execute_fix(fixer['id'], alert_id, fix_type='auto', executed_by='system')
                else:
                    if self._approval_manager:
                        self._approval_manager.create_approval(
                            fix_id=fixer['id'],
                            fix_name=fixer['name'],
                            alert_id=alert_id,
                            risk_level=risk,
                            fix_description=fixer['description'],
                        )
        except Exception as e:
            logger.error(f'自动修复流程异常: {e}')

    def execute_fix(self, fix_id, alert_id=None, fix_type='manual', executed_by='developer'):
        """执行指定修复"""
        registry = self.get_fix_registry()
        fixer = next((f for f in registry if f['id'] == fix_id), None)
        if not fixer:
            return {'success': False, 'error': f'修复器 {fix_id} 不存在'}

        return self._execute_fix(fix_id, alert_id, fix_type=fix_type, executed_by=executed_by)

    def _execute_fix(self, fix_id, alert_id=None, fix_type='manual', executed_by='developer'):
        """执行修复并记录结果"""
        start_time = time.time()

        record = self._create_fix_record(fix_id, alert_id, fix_type, executed_by)

        try:
            action_func = getattr(self, f'_fix_{fix_id}', None)
            if not action_func:
                self._update_fix_record(record, 'failed', {'error': '修复函数不存在'})
                return {'success': False, 'error': '修复函数不存在'}

            result = action_func()
            duration_ms = int((time.time() - start_time) * 1000)

            status = 'success' if result.get('success') else 'failed'
            self._update_fix_record(record, status, result, duration_ms)

            self._write_evolution_log(fix_id, alert_id, result, status)

            if self.wecom_bot:
                self.wecom_bot.send_fix_result(
                    fix_id=fix_id,
                    fix_name=self._get_fix_name(fix_id),
                    status=status,
                    result=result,
                    alert_id=alert_id,
                )

            return {'success': result.get('success'), 'result': result, 'record_id': record.id}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_result = {'error': str(e)}
            self._update_fix_record(record, 'failed', error_result, duration_ms)
            return {'success': False, 'error': str(e)}

    def _match_fixer(self, alert, registry):
        """根据告警内容匹配修复器"""
        title = (alert.title or '').lower()
        description = (alert.description or '').lower()
        text = title + ' ' + description

        for fixer in registry:
            for keyword in fixer['match_keywords']:
                if keyword.lower() in text:
                    return fixer
        return None

    # ==================== 修复器实现 ====================

    def _fix_db_reconnect(self):
        """数据库连接恢复"""
        try:
            with self.app.app_context():
                self.db.session.execute(self.db.text('SELECT 1'))
                self.db.session.commit()
                return {'success': True, 'message': '数据库连接已恢复', 'detail': 'SELECT 1 执行成功'}
        except Exception as e:
            try:
                self.db.session.rollback()
                self.db.session.execute(self.db.text('SELECT 1'))
                return {'success': True, 'message': '数据库连接已通过回滚重建', 'detail': str(e)}
            except Exception as e2:
                return {'success': False, 'message': '数据库连接恢复失败', 'detail': str(e2)}

    def _fix_redis_recovery(self):
        """Redis 连接恢复"""
        if not self.redis:
            return {'success': False, 'message': 'Redis 未配置'}

        try:
            self.redis.ping()
            return {'success': True, 'message': 'Redis 连接正常，无需修复'}
        except Exception:
            try:
                if hasattr(self.redis, 'connection_pool'):
                    self.redis.connection_pool.disconnect()
                self.redis.ping()
                return {'success': True, 'message': 'Redis 连接池已重建'}
            except Exception as e:
                return {'success': False, 'message': 'Redis 恢复失败', 'detail': str(e)}

    def _fix_memory_relief(self):
        """内存清理"""
        try:
            import psutil
            before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            gc.collect()

            after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            freed = round(before - after, 1)

            return {
                'success': True,
                'message': f'内存清理完成，释放 {freed}MB',
                'detail': f'清理前: {round(before, 1)}MB, 清理后: {round(after, 1)}MB',
            }
        except ImportError:
            gc.collect()
            return {'success': True, 'message': '已执行 gc.collect()（psutil 未安装，无法量化）'}
        except Exception as e:
            return {'success': False, 'message': '内存清理失败', 'detail': str(e)}

    def _fix_disk_cleanup(self):
        """磁盘清理（仅清理应用临时目录，不触碰系统日志）"""
        cleaned = []
        total_freed = 0

        tmp_dirs = ['/tmp/hairstyle-transfer', '/tmp/flask']
        for tmp_dir in tmp_dirs:
            if os.path.exists(tmp_dir):
                size = self._get_dir_size(tmp_dir)
                try:
                    import shutil
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    cleaned.append(tmp_dir)
                    total_freed += size
                except Exception:
                    pass

        return {
            'success': True,
            'message': f'磁盘清理完成，清理 {len(cleaned)} 个临时目录',
            'detail': f'释放约 {round(total_freed / 1024 / 1024, 1)}MB',
        }

    def _fix_slow_query_kill(self):
        """慢查询清理"""
        try:
            with self.app.app_context():
                result = self.db.session.execute(
                    self.db.text("SHOW PROCESSLIST")
                ).fetchall()

                killed = []
                for row in result:
                    proc_id = row[0]
                    time_val = row[5]
                    state = row[6] if len(row) > 6 else ''
                    info = row[7] if len(row) > 7 else ''

                    if time_val and int(time_val) > 30 and state != 'Sleep':
                        try:
                            self.db.session.execute(self.db.text(f"KILL {proc_id}"))
                            killed.append({
                                'id': proc_id,
                                'time': int(time_val),
                                'info': str(info)[:100],
                            })
                        except Exception:
                            pass

                if killed:
                    return {
                        'success': True,
                        'message': f'已清理 {len(killed)} 个慢查询',
                        'detail': json.dumps(killed, ensure_ascii=False),
                    }
                else:
                    return {'success': True, 'message': '未发现需要清理的慢查询'}

        except Exception as e:
            return {'success': False, 'message': '慢查询清理失败', 'detail': str(e)}

    def _fix_domain_config_check(self):
        """域名配置检查"""
        try:
            import socket
            from urllib.parse import urlparse

            issues = []
            checked = []

            # 检查虚拟支付回调地址
            notify_url = os.getenv('WECHAT_VIRTUAL_PAY_NOTIFY_URL', '')
            if notify_url:
                parsed = urlparse(notify_url)
                domain = parsed.hostname
                if domain:
                    try:
                        socket.gethostbyname(domain)
                        checked.append({'domain': domain, 'type': 'callback_url', 'status': 'ok'})
                    except socket.gaierror:
                        issues.append({
                            'domain': domain,
                            'type': 'callback_url',
                            'url': notify_url,
                            'status': 'error',
                            'message': '域名无法解析'
                        })

            # 检查关键第三方服务域名
            critical_domains = [
                ('api.mch.weixin.qq.com', 'wechat_pay_api'),
                ('facebody.cn-shanghai.aliyuncs.com', 'aliyun_facebody'),
                ('dashscope.aliyuncs.com', 'aliyun_dashscope'),
            ]

            for domain, service_type in critical_domains:
                try:
                    socket.gethostbyname(domain)
                    checked.append({'domain': domain, 'type': service_type, 'status': 'ok'})
                except socket.gaierror:
                    issues.append({
                        'domain': domain,
                        'type': service_type,
                        'status': 'error',
                        'message': 'DNS 解析失败'
                    })

            if issues:
                # 发送告警通知
                if self.wecom_bot:
                    markdown_msg = f"## ⚠️ 域名配置异常告警\n\n"
                    text_msg = "[域名配置异常告警]\n"
                    for issue in issues:
                        markdown_msg += f"- **域名**: {issue['domain']}\n"
                        markdown_msg += f"  - 类型: {issue['type']}\n"
                        markdown_msg += f"  - 状态: {issue['message']}\n"
                        if 'url' in issue:
                            markdown_msg += f"  - URL: {issue['url']}\n"
                        markdown_msg += "\n"
                        text_msg += f"域名: {issue['domain']}, 类型: {issue['type']}, 状态: {issue['message']}\n"
                        if 'url' in issue:
                            text_msg += f"URL: {issue['url']}\n"
                    markdown_msg += "---\n请及时检查并修正域名配置。"
                    text_msg += "请及时检查并修正域名配置。"
                    self.wecom_bot._send(markdown_msg, text_msg)

                return {
                    'success': True,
                    'message': f'发现 {len(issues)} 个域名配置异常',
                    'detail': json.dumps({'issues': issues, 'checked': checked}, ensure_ascii=False),
                }
            else:
                return {
                    'success': True,
                    'message': f'所有域名配置正常（已检查 {len(checked)} 个域名）',
                    'detail': json.dumps({'checked': checked}, ensure_ascii=False),
                }

        except Exception as e:
            return {'success': False, 'message': f'域名配置检查失败: {str(e)}'}

    # ==================== 辅助方法 ====================

    def _get_alert(self, alert_id):
        from .models import SystemAlert
        return self.db.session.query(SystemAlert).get(alert_id)

    def _create_fix_record(self, fix_id, alert_id, fix_type, executed_by):
        from .models import FixExecution
        record = FixExecution(
            fix_id=fix_id,
            fix_name=self._get_fix_name(fix_id),
            alert_id=alert_id,
            fix_type=fix_type,
            risk_level=self._get_fix_risk(fix_id),
            status='running',
            executed_by=executed_by,
        )
        self.db.session.add(record)
        self.db.session.commit()
        return record

    def _update_fix_record(self, record, status, result, duration_ms=None):
        record.status = status
        record.result_detail = json.dumps(result, ensure_ascii=False)
        if duration_ms is not None:
            record.duration_ms = duration_ms
        self.db.session.commit()

    def _write_evolution_log(self, fix_id, alert_id, result, status):
        from .models import EvolutionLog
        log = EvolutionLog(
            log_type='fix',
            related_alert_id=alert_id,
            title=f'自动修复: {self._get_fix_name(fix_id)}',
            description=f'修复器 {fix_id} 执行{status}',
            action_taken=json.dumps(result, ensure_ascii=False),
            created_by='system',
        )
        self.db.session.add(log)
        self.db.session.commit()

    def _get_fix_name(self, fix_id):
        registry = self.get_fix_registry()
        fixer = next((f for f in registry if f['id'] == fix_id), None)
        return fixer['name'] if fixer else fix_id

    def _get_fix_risk(self, fix_id):
        registry = self.get_fix_registry()
        fixer = next((f for f in registry if f['id'] == fix_id), None)
        return fixer['risk'] if fixer else 'unknown'

    def _get_dir_size(self, path):
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
        except Exception:
            pass
        return total
