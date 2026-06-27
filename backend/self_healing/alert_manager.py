#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警管理器
负责告警的创建、去重、限流、持久化和异步通知
"""

import hashlib
import json
import logging
import queue
import threading
import time
from datetime import datetime

logger = logging.getLogger('self_healing')


class AlertManager:
    """告警管理器"""

    def __init__(self, app, config, db=None, redis_client=None, wecom_bot=None,
                 fixer=None, rule_engine=None, bug_recorder=None):
        self.app = app
        self.config = config
        self.db = db
        self.redis = redis_client
        self.wecom_bot = wecom_bot
        self.fixer = fixer
        self.rule_engine = rule_engine
        self.bug_recorder = bug_recorder

        self._queue = queue.Queue(maxsize=config.get('ALERT_QUEUE_MAXSIZE', 1000))
        self._worker_thread = None
        self._running = False

        # 内存降级缓存（Redis不可用时）
        self._memory_dedup = {}
        self._memory_notify_count = {}
        self._dedup_call_count = 0

    def start(self):
        """启动后台Worker线程"""
        if not self.config.get('ALERT_WORKER_ENABLED', True):
            logger.info('Alert Worker 已禁用（ALERT_WORKER_ENABLED=false）')
            return

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name='self_healing_alert_worker'
        )
        self._worker_thread.start()
        logger.info('Alert Worker 线程已启动')

    def stop(self):
        """停止Worker线程"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)

    def record_alert(self, alert_type, severity, title, description='',
                     stack_trace=None, request_url=None, request_method=None,
                     request_params=None, response_data=None,
                     user_id=None, user_type=None, environment_info=None,
                     source_module=None):
        """
        记录告警（同步写入DB + 异步推送通知）

        Returns:
            alert_id 或 None（如果去重命中）
        """
        from .sanitizer import (
            sanitize_request_params, sanitize_stack_trace,
            sanitize_headers, sanitize_dict
        )

        max_stack = self.config.get('MAX_STACK_TRACE_LEN', 4096)
        max_params = self.config.get('MAX_REQUEST_PARAMS_LEN', 2048)
        max_response = self.config.get('MAX_RESPONSE_DATA_LEN', 2048)

        # 脱敏
        stack_trace = sanitize_stack_trace(stack_trace, max_stack)
        request_params = sanitize_request_params(request_params, max_params)
        if response_data:
            response_data = sanitize_dict(response_data, max_response)

        # 去重检查
        dedup_key = self._make_dedup_key(alert_type, source_module, title)
        if self._is_duplicate(dedup_key):
            logger.debug(f'告警去重命中: {title}')
            return None

        # 写入数据库
        alert_id = None
        try:
            with self.app.app_context():
                alert_id = self._save_alert(
                    alert_type=alert_type,
                    severity=severity,
                    title=title,
                    description=description,
                    stack_trace=stack_trace,
                    request_url=request_url,
                    request_method=request_method,
                    request_params=request_params,
                    response_data=json.dumps(response_data, ensure_ascii=False) if response_data else None,
                    user_id=user_id,
                    user_type=user_type,
                    environment_info=json.dumps(environment_info, ensure_ascii=False) if environment_info else None,
                    source_module=source_module,
                )

                # 搜索相似历史 Bug 并存储
                if alert_id and self.bug_recorder:
                    try:
                        search_text = (title or '') + ' ' + (description or '')
                        similar = self.bug_recorder.search_similar_bugs(search_text)
                        if similar:
                            from .models import SystemAlert
                            alert_obj = self.db.session.query(SystemAlert).get(alert_id)
                            if alert_obj:
                                alert_obj.similar_bugs = json.dumps(
                                    [{'bug_id': b.get('bug_id'), 'title': b.get('title'),
                                      'fix_description': b.get('fix_description', '')[:200]}
                                     for b in similar[:5]],
                                    ensure_ascii=False,
                                )
                                self.db.session.commit()
                    except Exception as e:
                        logger.debug(f'相似Bug搜索失败: {e}')
        except Exception as e:
            logger.error(f'告警DB写入失败: {e}')

        # 放入异步通知队列
        if alert_id and self.wecom_bot:
            try:
                self._queue.put_nowait({
                    'alert_id': alert_id,
                    'alert_type': alert_type,
                    'severity': severity,
                    'title': title,
                    'description': description,
                    'source_module': source_module,
                    'dedup_key': dedup_key,
                })
            except queue.Full:
                logger.warning('告警通知队列已满，丢弃最旧告警')
                try:
                    self._queue.get_nowait()
                    self._queue.put_nowait({
                        'alert_id': alert_id,
                        'alert_type': alert_type,
                        'severity': severity,
                        'title': title,
                        'description': description,
                        'source_module': source_module,
                        'dedup_key': dedup_key,
                    })
                except queue.Full:
                    pass

        # Phase 2: 触发自动修复
        if alert_id and self.fixer and self.config.get('AUTO_FIX_ENABLED', True):
            try:
                t = threading.Thread(
                    target=self.fixer.try_auto_fix,
                    args=(alert_id,),
                    daemon=True,
                    name=f'sh_autofix_{alert_id}',
                )
                t.start()
            except Exception as e:
                logger.error(f'自动修复触发失败: {e}')

        return alert_id

    def _worker_loop(self):
        """后台Worker循环：从队列取告警并发送企业微信通知"""
        while self._running:
            try:
                alert = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                self._send_notification(alert)
            except Exception as e:
                logger.error(f'告警通知发送失败: {e}')
            finally:
                self._queue.task_done()

    def _send_notification(self, alert):
        """发送企业微信通知（带限流）"""
        dedup_key = alert.get('dedup_key', '')

        # 通知限流检查
        if not self._should_notify(dedup_key):
            logger.debug(f'告警通知限流: {alert["title"]}')
            return

        # 全局频率检查
        if not self._check_global_rate_limit():
            logger.warning('全局通知频率上限，静默写入DB')
            return

        if self.wecom_bot:
            self.wecom_bot.send_alert(alert)

    def _make_dedup_key(self, alert_type, source_module, title):
        raw = f'{alert_type}:{source_module or ""}:{title}'
        return hashlib.md5(raw.encode()).hexdigest()

    def _is_duplicate(self, dedup_key):
        """检查是否为重复告警"""
        window = self.config.get('ALERT_DEDUP_WINDOW', 300)

        if self.redis:
            try:
                key = f'sh:dedup:{dedup_key}'
                if self.redis.exists(key):
                    return True
                self.redis.setex(key, window, '1')
                return False
            except Exception:
                pass

        # 内存降级
        now = time.time()
        if dedup_key in self._memory_dedup:
            if now - self._memory_dedup[dedup_key] < window:
                return True
        self._memory_dedup[dedup_key] = now

        # 每 100 次调用才执行一次过期清理，避免每次请求都做 O(n) 扫描
        self._dedup_call_count += 1
        if self._dedup_call_count >= 100:
            self._dedup_call_count = 0
            expired = [k for k, v in self._memory_dedup.items() if now - v > window]
            for k in expired:
                del self._memory_dedup[k]

        return False

    def _should_notify(self, dedup_key):
        """通知限流：同一告警key在冷却期内仅发送1次"""
        cooldown = self.config.get('ALERT_NOTIFY_COOLDOWN', 60)

        if self.redis:
            try:
                key = f'sh:notify:{dedup_key}'
                lua_script = """
                local count = redis.call('incr', KEYS[1])
                if count == 1 then
                    redis.call('expire', KEYS[1], ARGV[1])
                end
                return count
                """
                count = self.redis.eval(lua_script, 1, key, cooldown)
                return count == 1
            except Exception:
                pass

        now = time.time()
        if dedup_key in self._memory_notify_count:
            last_time, count = self._memory_notify_count[dedup_key]
            if now - last_time < cooldown:
                return False
        self._memory_notify_count[dedup_key] = (now, 1)
        return True

    def _check_global_rate_limit(self):
        """全局频率上限"""
        max_per_min = self.config.get('ALERT_NOTIFY_MAX_PER_MIN', 10)

        if self.redis:
            try:
                key = 'sh:global_notify'
                now = int(time.time())
                window_key = f'{key}:{now // 60}'
                count = self.redis.incr(window_key)
                if count == 1:
                    self.redis.expire(window_key, 120)
                return count <= max_per_min
            except Exception:
                pass

        return True

    def _save_alert(self, **kwargs):
        """保存告警到数据库"""
        if not self.db:
            logger.warning('数据库未配置，告警仅记录日志')
            return None

        from .models import SystemAlert
        alert = SystemAlert(**kwargs)
        self.db.session.add(alert)
        self.db.session.commit()
        return alert.id
