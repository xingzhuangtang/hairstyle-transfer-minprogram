// api/monitor.js - 系统监控 API 封装
import { get, put } from '../utils/request.js'

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
