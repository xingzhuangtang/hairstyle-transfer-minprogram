// api/monitor.js - 系统监控 API 封装
import { get, put, post, del } from '../utils/request.js'

// Phase 1: 告警 & 健康
export function getAlerts(params) {
  return get('/api/dev/monitor/alerts', params)
}

export function getAlertDetail(id) {
  return get(`/api/dev/monitor/alerts/${id}`)
}

export function acknowledgeAlert(id) {
  return put(`/api/dev/monitor/alerts/${id}/acknowledge`)
}

export function resolveAlert(id, data) {
  return put(`/api/dev/monitor/alerts/${id}/resolve`, data)
}

export function getAlertStats() {
  return get('/api/dev/monitor/alert-stats')
}

export function getSystemHealth() {
  return get('/api/dev/monitor/system-health')
}

export function getEvolutionLogs(params) {
  return get('/api/dev/monitor/evolution-logs', params)
}

// Phase 2: 自动修复
export function getFixList() {
  return get('/api/dev/monitor/fix/list')
}

export function executeFix(data) {
  return post('/api/dev/monitor/fix/execute', data)
}

export function getFixHistory(params) {
  return get('/api/dev/monitor/fix/history', params)
}

// Phase 2: 审批流
export function getApprovals(params) {
  return get('/api/dev/monitor/approvals', params)
}

export function approveFix(id) {
  return put(`/api/dev/monitor/approvals/${id}/approve`)
}

export function rejectFix(id) {
  return put(`/api/dev/monitor/approvals/${id}/reject`)
}

// Phase 3: 防御规则
export function getDefenseRules() {
  return get('/api/dev/monitor/defense/rules')
}

export function createDefenseRule(data) {
  return post('/api/dev/monitor/defense/rules', data)
}

export function updateDefenseRule(id, data) {
  return put(`/api/dev/monitor/defense/rules/${id}`, data)
}

export function deleteDefenseRule(id) {
  return del(`/api/dev/monitor/defense/rules/${id}`)
}

// Phase 3: 进化分析
export function runEvolutionAnalysis() {
  return post('/api/dev/monitor/evolution/analyze')
}

export function getEvolutionReport() {
  return get('/api/dev/monitor/evolution/report')
}

export function getHealthScore() {
  return get('/api/dev/monitor/health-score')
}
