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
    verification_status = Column(String(32), comment='验证状态: pending/verified/failed')
    verified_at = Column(DateTime, comment='验证时间')
    bug_knowledge_id = Column(String(64), comment='关联Bug知识库ID')
    similar_bugs = Column(Text, comment='相似历史Bug JSON')
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
            'verification_status': self.verification_status,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'bug_knowledge_id': self.bug_knowledge_id,
            'similar_bugs': self.similar_bugs,
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


class FixExecution(Base):
    """修复执行记录"""
    __tablename__ = 'fix_executions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fix_id = Column(String(64), nullable=False, comment='修复器ID')
    fix_name = Column(String(128), comment='修复器名称')
    alert_id = Column(Integer, comment='关联告警ID')
    fix_type = Column(String(16), nullable=False, comment='类型: auto/manual/approved')
    risk_level = Column(String(16), comment='风险级别: low/medium/high')
    status = Column(String(16), nullable=False, default='running', comment='状态: running/success/failed/skipped')
    result_detail = Column(Text, comment='执行结果JSON')
    duration_ms = Column(Integer, comment='执行耗时(毫秒)')
    executed_by = Column(String(128), comment='执行人')
    executed_at = Column(DateTime, nullable=False, default=datetime.now, comment='执行时间')

    __table_args__ = (
        Index('idx_fix_alert', 'alert_id'),
        Index('idx_fix_status', 'status'),
        Index('idx_fix_executed_at', 'executed_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'fix_id': self.fix_id,
            'fix_name': self.fix_name,
            'alert_id': self.alert_id,
            'fix_type': self.fix_type,
            'risk_level': self.risk_level,
            'status': self.status,
            'result_detail': self.result_detail,
            'duration_ms': self.duration_ms,
            'executed_by': self.executed_by,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
        }


class ApprovalRecord(Base):
    """审批记录"""
    __tablename__ = 'approval_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fix_id = Column(String(64), nullable=False, comment='修复器ID')
    fix_name = Column(String(128), comment='修复器名称')
    alert_id = Column(Integer, comment='关联告警ID')
    risk_level = Column(String(16), comment='风险级别')
    fix_description = Column(Text, comment='修复方案描述')
    status = Column(String(16), nullable=False, default='pending', comment='状态: pending/approved/rejected/expired')
    requested_by = Column(String(128), comment='发起人')
    approved_by = Column(String(128), comment='审批人')
    approved_at = Column(DateTime, comment='审批时间')
    fix_result = Column(Text, comment='修复结果JSON')
    executed_at = Column(DateTime, comment='执行时间')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    expires_at = Column(DateTime, comment='过期时间')

    __table_args__ = (
        Index('idx_approval_status', 'status'),
        Index('idx_approval_alert', 'alert_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'fix_id': self.fix_id,
            'fix_name': self.fix_name,
            'alert_id': self.alert_id,
            'risk_level': self.risk_level,
            'fix_description': self.fix_description,
            'status': self.status,
            'requested_by': self.requested_by,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'fix_result': self.fix_result,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class DefenseRule(Base):
    """防御规则表"""
    __tablename__ = 'defense_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, comment='规则名称')
    enabled = Column(Integer, nullable=False, default=1, comment='是否启用: 0/1')
    priority = Column(Integer, nullable=False, default=100, comment='优先级(越小越高)')
    pattern_type = Column(String(32), nullable=False, comment='模式类型: title_contains/regex/source_module/frequency')
    pattern_value = Column(String(512), nullable=False, comment='模式值')
    action = Column(String(16), nullable=False, comment='动作: auto_fix/warn/suppress')
    action_config = Column(Text, comment='动作配置JSON（如关联的fix_id）')
    cooldown_seconds = Column(Integer, nullable=False, default=300, comment='冷却时间(秒)')
    hit_count = Column(Integer, nullable=False, default=0, comment='命中次数')
    last_hit_at = Column(DateTime, comment='最后命中时间')
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_rule_enabled', 'enabled', 'priority'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'enabled': bool(self.enabled),
            'priority': self.priority,
            'pattern_type': self.pattern_type,
            'pattern_value': self.pattern_value,
            'action': self.action,
            'action_config': self.action_config,
            'cooldown_seconds': self.cooldown_seconds,
            'hit_count': self.hit_count,
            'last_hit_at': self.last_hit_at.isoformat() if self.last_hit_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BugKnowledge(Base):
    """Bug 知识库表 — 结构化记录已修复的 Bug，防止复发"""
    __tablename__ = 'bug_knowledge'

    id = Column(Integer, primary_key=True, autoincrement=True)
    bug_id = Column(String(64), unique=True, nullable=False, comment='Bug唯一标识')
    title = Column(String(256), nullable=False, comment='Bug标题')
    category = Column(String(32), nullable=False, comment='分类: data_type/deployment/security/performance/logic')
    severity = Column(String(16), nullable=False, comment='严重级别: low/medium/high/critical')
    root_cause = Column(Text, comment='根因分析')
    affected_files = Column(Text, comment='受影响文件列表JSON')
    fix_description = Column(Text, comment='修复方案')
    prevention = Column(Text, comment='预防措施')
    related_alert_id = Column(Integer, comment='关联告警ID')
    related_evolution_log_id = Column(Integer, comment='关联进化日志ID')
    status = Column(String(16), nullable=False, default='active', comment='状态: active/archived')
    discovered_at = Column(DateTime, comment='发现时间')
    fixed_at = Column(DateTime, comment='修复时间')
    verification_count = Column(Integer, nullable=False, default=0, comment='验证次数')
    success_count = Column(Integer, nullable=False, default=0, comment='验证成功次数')
    confidence = Column(Float, nullable=False, default=0, comment='置信度')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_bug_category', 'category'),
        Index('idx_bug_status', 'status'),
        Index('idx_bug_severity', 'severity'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'bug_id': self.bug_id,
            'title': self.title,
            'category': self.category,
            'severity': self.severity,
            'root_cause': self.root_cause,
            'affected_files': self.affected_files,
            'fix_description': self.fix_description,
            'prevention': self.prevention,
            'related_alert_id': self.related_alert_id,
            'related_evolution_log_id': self.related_evolution_log_id,
            'status': self.status,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None,
            'fixed_at': self.fixed_at.isoformat() if self.fixed_at else None,
            'verification_count': self.verification_count,
            'success_count': self.success_count,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
