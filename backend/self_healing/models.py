#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自愈系统数据模型
独立于主项目的 models.py，使用独立的 SQLAlchemy metadata
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class SystemAlert(Base):
    """异常/预警记录表"""
    __tablename__ = 'system_alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(32), nullable=False, comment='类型: error/warning/performance/security')
    severity = Column(String(16), nullable=False, default='medium', comment='严重级别: low/medium/high/critical')
    title = Column(String(256), nullable=False, comment='告警标题')
    description = Column(Text, comment='详细描述')
    stack_trace = Column(Text, comment='异常堆栈（脱敏后）')
    request_url = Column(String(512), comment='请求URL')
    request_method = Column(String(16), comment='请求方法')
    request_params = Column(Text, comment='请求参数（脱敏后）')
    response_data = Column(Text, comment='响应数据摘要（脱敏后）')
    user_id = Column(Integer, comment='关联用户ID')
    user_type = Column(String(32), comment='用户类型')
    environment_info = Column(Text, comment='环境信息JSON')
    source_module = Column(String(128), comment='来源模块')
    status = Column(String(32), nullable=False, default='new', comment='状态: new/acknowledged/resolved/ignored')
    resolved_by = Column(String(128), comment='解决人')
    resolved_at = Column(DateTime, comment='解决时间')
    resolve_note = Column(Text, comment='解决备注')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_alert_type_status', 'alert_type', 'status'),
        Index('idx_severity_created', 'severity', 'created_at'),
        Index('idx_source_module', 'source_module'),
        Index('idx_created_at', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'stack_trace': self.stack_trace,
            'request_url': self.request_url,
            'request_method': self.request_method,
            'request_params': self.request_params,
            'response_data': self.response_data,
            'user_id': self.user_id,
            'user_type': self.user_type,
            'environment_info': self.environment_info,
            'source_module': self.source_module,
            'status': self.status,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolve_note': self.resolve_note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EvolutionLog(Base):
    """进化档案表（Phase 1 建表预留，Phase 2/3 填充）"""
    __tablename__ = 'evolution_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_type = Column(String(32), nullable=False, comment='类型: fix/rule/evolution')
    related_alert_id = Column(Integer, comment='关联告警ID')
    title = Column(String(256), comment='标题')
    description = Column(Text, comment='描述')
    action_taken = Column(Text, comment='执行的修复动作')
    rule_pattern = Column(Text, comment='防御规则模式JSON（Phase 2）')
    effect = Column(Text, comment='效果评估JSON（Phase 3）')
    created_by = Column(String(128), comment='创建人')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_log_type', 'log_type'),
        Index('idx_related_alert', 'related_alert_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'log_type': self.log_type,
            'related_alert_id': self.related_alert_id,
            'title': self.title,
            'description': self.description,
            'action_taken': self.action_taken,
            'rule_pattern': self.rule_pattern,
            'effect': self.effect,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
