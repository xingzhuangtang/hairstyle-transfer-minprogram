// pages/monitor/monitor.js
import {
  getAlerts, getAlertDetail, acknowledgeAlert, resolveAlert, getAlertStats, getSystemHealth,
  getFixList, executeFix, getFixHistory, getApprovals, approveFix, rejectFix,
  getDefenseRules, runEvolutionAnalysis, getEvolutionReport, getHealthScore,
} from '../../api/monitor.js'

Page({
  data: {
    activeTab: 0,
    tabs: ['告警', '健康', '修复', '进化'],

    // Tab 0: 告警列表
    alerts: [],
    alertStats: null,
    alertLoading: false,
    alertPage: 1,
    alertNoMore: false,
    filterStatus: '',
    filterSeverity: '',
    statusOptions: ['全部状态', '待处理', '已确认', '已解决', '已忽略'],
    statusValues: ['', 'new', 'acknowledged', 'resolved', 'ignored'],
    statusIndex: 0,
    severityOptions: ['全部级别', '严重', '高危', '中危', '低危'],
    severityValues: ['', 'critical', 'high', 'medium', 'low'],
    severityIndex: 0,

    // 告警详情弹窗
    showDetail: false,
    currentAlert: null,
    detailLoading: false,

    // Tab 1: 系统健康
    healthData: null,
    healthLoading: false,
    healthTimer: null,

    // Tab 2: 自动修复
    fixList: [],
    fixHistory: [],
    approvals: [],
    fixLoading: false,
    fixSubTab: 0,
    fixExecuting: '',

    // Tab 3: 进化分析
    healthScore: null,
    evolutionReport: null,
    defenseRules: [],
    evolutionLoading: false,
    evolutionSubTab: 0,
  },

  onLoad() {
    this.loadAlertStats()
    this.loadAlerts(true)
  },

  onShow() {
    if (this.data.activeTab === 1) {
      this.startHealthPolling()
    }
  },

  onHide() {
    this.stopHealthPolling()
  },

  onUnload() {
    this.stopHealthPolling()
  },

  // ==================== Tab 切换 ====================

  onTabChange(e) {
    const tab = parseInt(e.currentTarget.dataset.tab)
    if (tab === this.data.activeTab) return

    this.stopHealthPolling()
    this.setData({ activeTab: tab })

    if (tab === 0) {
      this.loadAlertStats()
      this.loadAlerts(true)
    } else if (tab === 1) {
      this.loadSystemHealth()
      this.startHealthPolling()
    } else if (tab === 2) {
      this.loadFixData()
    } else if (tab === 3) {
      this.loadEvolutionData()
    }
  },

  // ==================== Tab 0: 告警列表 ====================

  async loadAlertStats() {
    try {
      const res = await getAlertStats()
      if (res.success) this.setData({ alertStats: res.data })
    } catch (e) {
      console.error('加载告警统计失败:', e)
    }
  },

  async loadAlerts(refresh = false) {
    if (this.data.alertLoading) return
    this.setData({ alertLoading: true })
    if (refresh) this.setData({ alertPage: 1, alertNoMore: false, alerts: [] })

    try {
      const { alertPage, filterStatus, filterSeverity } = this.data
      const res = await getAlerts({ page: alertPage, page_size: 20, status: filterStatus, severity: filterSeverity })
      if (res.success) {
        const items = (res.data.items || []).map(a => this._formatAlert(a))
        this.setData({
          alerts: refresh ? items : [...this.data.alerts, ...items],
          alertNoMore: res.data.page >= res.data.total_pages,
          alertPage: alertPage + 1,
        })
      }
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ alertLoading: false })
    }
  },

  _formatAlert(a) {
    const severityColors = { critical: '#ff4d4f', high: '#fa8c16', medium: '#fadb14', low: '#52c41a' }
    const severityLabels = { critical: '严重', high: '高危', medium: '中危', low: '低危' }
    const statusLabels = { new: '待处理', acknowledged: '已确认', resolved: '已解决', ignored: '已忽略' }
    return {
      ...a,
      severityColor: severityColors[a.severity] || '#999',
      severityLabel: severityLabels[a.severity] || a.severity,
      statusLabel: statusLabels[a.status] || a.status,
      timeText: this._formatRelativeTime(a.created_at),
      titleShort: a.title && a.title.length > 30 ? a.title.substring(0, 30) + '...' : (a.title || ''),
    }
  },

  onStatusFilterChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ statusIndex: idx, filterStatus: this.data.statusValues[idx], alerts: [], alertPage: 1, alertNoMore: false })
    this.loadAlerts(true)
  },

  onSeverityFilterChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ severityIndex: idx, filterSeverity: this.data.severityValues[idx], alerts: [], alertPage: 1, alertNoMore: false })
    this.loadAlerts(true)
  },

  async onAlertTap(e) {
    const id = e.currentTarget.dataset.id
    this.setData({ showDetail: true, detailLoading: true, currentAlert: null })
    try {
      const res = await getAlertDetail(id)
      if (res.success) this.setData({ currentAlert: this._formatAlert(res.data), detailLoading: false })
    } catch (e) {
      this.setData({ detailLoading: false })
    }
  },

  closeDetail() { this.setData({ showDetail: false, currentAlert: null }) },

  async onAcknowledge() {
    const alert = this.data.currentAlert
    if (!alert) return
    try {
      const res = await acknowledgeAlert(alert.id)
      if (res.success) {
        wx.showToast({ title: '已确认', icon: 'success' })
        this.closeDetail(); this.loadAlerts(true); this.loadAlertStats()
      }
    } catch (e) { wx.showToast({ title: '操作失败', icon: 'none' }) }
  },

  async onResolve() {
    const alert = this.data.currentAlert
    if (!alert) return
    try {
      const res = await resolveAlert(alert.id, { resolved_by: 'developer', note: '手动解决' })
      if (res.success) {
        wx.showToast({ title: '已解决', icon: 'success' })
        this.closeDetail(); this.loadAlerts(true); this.loadAlertStats()
      }
    } catch (e) { wx.showToast({ title: '操作失败', icon: 'none' }) }
  },

  loadMoreAlerts() { if (!this.data.alertNoMore && !this.data.alertLoading) this.loadAlerts(false) },
  onAlertScrollToLower() { this.loadMoreAlerts() },

  // ==================== Tab 1: 系统健康 ====================

  async loadSystemHealth() {
    if (this.data.healthLoading) return
    this.setData({ healthLoading: true })
    try {
      const res = await getSystemHealth()
      if (res.success) this.setData({ healthData: res.data })
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally { this.setData({ healthLoading: false }) }
  },

  startHealthPolling() {
    this.stopHealthPolling()
    this.data.healthTimer = setInterval(() => this.loadSystemHealth(), 30000)
  },

  stopHealthPolling() {
    if (this.data.healthTimer) { clearInterval(this.data.healthTimer); this.data.healthTimer = null }
  },

  onRefreshHealth() { this.loadSystemHealth() },

  // ==================== Tab 2: 自动修复 ====================

  onFixSubTabChange(e) {
    this.setData({ fixSubTab: parseInt(e.currentTarget.dataset.sub) })
  },

  async loadFixData() {
    this.setData({ fixLoading: true })
    try {
      const [listRes, historyRes, approvalRes] = await Promise.all([
        getFixList(), getFixHistory({ page: 1, page_size: 10 }), getApprovals({ page: 1, page_size: 10 }),
      ])
      this.setData({
        fixList: listRes.success ? listRes.data : [],
        fixHistory: historyRes.success ? (historyRes.data.items || []).map(h => ({
          ...h,
          statusIcon: h.status === 'success' ? '✅' : h.status === 'failed' ? '❌' : '⏳',
          statusText: { success: '成功', failed: '失败', running: '执行中', skipped: '跳过' }[h.status] || h.status,
          timeText: this._formatRelativeTime(h.executed_at),
        })) : [],
        approvals: approvalRes.success ? (approvalRes.data.items || []).map(a => ({
          ...a,
          riskLabel: { low: '低危', medium: '中危', high: '高危' }[a.risk_level] || a.risk_level,
          statusText: { pending: '待审批', approved: '已批准', rejected: '已拒绝', expired: '已过期' }[a.status] || a.status,
          timeText: this._formatRelativeTime(a.created_at),
        })) : [],
      })
    } catch (e) {
      console.error('加载修复数据失败:', e)
    } finally { this.setData({ fixLoading: false }) }
  },

  async onExecuteFix(e) {
    const fixId = e.currentTarget.dataset.id
    const fixer = this.data.fixList.find(f => f.id === fixId)

    wx.showModal({
      title: '确认执行',
      content: `确定执行「${fixer ? fixer.name : fixId}」？`,
      success: async (res) => {
        if (!res.confirm) return
        this.setData({ fixExecuting: fixId })
        try {
          const result = await executeFix({ fix_id: fixId })
          wx.showToast({ title: result.success ? '执行成功' : '执行失败', icon: result.success ? 'success' : 'none' })
          setTimeout(() => this.loadFixData(), 1000)
        } catch (e) {
          wx.showToast({ title: '执行异常', icon: 'none' })
        } finally { this.setData({ fixExecuting: '' }) }
      }
    })
  },

  async onApproveFix(e) {
    const id = e.currentTarget.dataset.id
    try {
      const res = await approveFix(id)
      wx.showToast({ title: res.success ? '已批准并执行' : '操作失败', icon: res.success ? 'success' : 'none' })
      setTimeout(() => this.loadFixData(), 1000)
    } catch (e) { wx.showToast({ title: '操作失败', icon: 'none' }) }
  },

  async onRejectFix(e) {
    const id = e.currentTarget.dataset.id
    try {
      const res = await rejectFix(id)
      wx.showToast({ title: res.success ? '已拒绝' : '操作失败', icon: res.success ? 'success' : 'none' })
      this.loadFixData()
    } catch (e) { wx.showToast({ title: '操作失败', icon: 'none' }) }
  },

  // ==================== Tab 3: 进化分析 ====================

  onEvolutionSubTabChange(e) {
    this.setData({ evolutionSubTab: parseInt(e.currentTarget.dataset.sub) })
  },

  async loadEvolutionData() {
    this.setData({ evolutionLoading: true })
    try {
      const [scoreRes, rulesRes] = await Promise.all([getHealthScore(), getDefenseRules()])
      const levelLabels = { excellent: '优秀', good: '良好', warning: '警告', critical: '危险' }
      const scoreData = scoreRes.success ? scoreRes.data : null
      if (scoreData) scoreData.levelLabel = levelLabels[scoreData.level] || scoreData.level
      this.setData({
        healthScore: scoreData,
        defenseRules: rulesRes.success ? (rulesRes.data || []).map(r => ({
          ...r,
          actionLabel: { auto_fix: '自动修复', warn: '告警', suppress: '抑制' }[r.action] || r.action,
          actionColor: { auto_fix: '#52c41a', warn: '#fa8c16', suppress: '#999' }[r.action] || '#999',
        })) : [],
      })
    } catch (e) {
      console.error('加载进化数据失败:', e)
    } finally { this.setData({ evolutionLoading: false }) }
  },

  async onRunAnalysis() {
    this.setData({ evolutionLoading: true })
    try {
      const res = await runEvolutionAnalysis()
      if (res.success) {
        this.setData({ evolutionReport: res.data })
        this.loadEvolutionData()
        wx.showToast({ title: '分析完成', icon: 'success' })
      }
    } catch (e) {
      wx.showToast({ title: '分析失败', icon: 'none' })
    } finally { this.setData({ evolutionLoading: false }) }
  },

  async onToggleRule(e) {
    const { id, enabled } = e.currentTarget.dataset
    try {
      const { updateDefenseRule } = await import('../../api/monitor.js')
      await updateDefenseRule(id, { enabled: !enabled })
      this.loadEvolutionData()
    } catch (e) { wx.showToast({ title: '操作失败', icon: 'none' }) }
  },

  // ==================== 下拉刷新 ====================

  onPullDownRefresh() {
    const tab = this.data.activeTab
    if (tab === 0) {
      Promise.all([this.loadAlertStats(), this.loadAlerts(true)]).finally(() => wx.stopPullDownRefresh())
    } else if (tab === 1) {
      this.loadSystemHealth().finally(() => wx.stopPullDownRefresh())
    } else if (tab === 2) {
      this.loadFixData(); wx.stopPullDownRefresh()
    } else if (tab === 3) {
      this.loadEvolutionData(); wx.stopPullDownRefresh()
    }
  },

  // ==================== 工具方法 ====================

  _formatRelativeTime(timeStr) {
    if (!timeStr) return '未知'
    const date = new Date(timeStr)
    const now = new Date()
    const diff = now - date
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)
    if (seconds < 60) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    if (days < 30) return `${days}天前`
    const y = date.getFullYear()
    const m = (date.getMonth() + 1).toString().padStart(2, '0')
    const d = date.getDate().toString().padStart(2, '0')
    return `${y}-${m}-${d}`
  },
})
