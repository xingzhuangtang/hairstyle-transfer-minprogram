// pages/monitor/monitor.js
import { getAlerts, getAlertDetail, acknowledgeAlert, resolveAlert, getAlertStats, getSystemHealth } from '../../api/monitor.js'

Page({
  data: {
    activeTab: 0,
    tabs: ['告警列表', '系统健康'],

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
  },

  onLoad() {
    this.loadAlertStats()
    this.loadAlerts(true)
  },

  onShow() {
    // 切换到系统健康Tab时开始轮询
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

    this.setData({ activeTab: tab })

    if (tab === 0) {
      this.loadAlertStats()
      this.loadAlerts(true)
    } else if (tab === 1) {
      this.loadSystemHealth()
      this.startHealthPolling()
    }
  },

  // ==================== Tab 0: 告警列表 ====================

  async loadAlertStats() {
    try {
      const res = await getAlertStats()
      if (res.success) {
        this.setData({ alertStats: res.data })
      }
    } catch (e) {
      console.error('加载告警统计失败:', e)
    }
  },

  async loadAlerts(refresh = false) {
    if (this.data.alertLoading) return
    this.setData({ alertLoading: true })

    if (refresh) {
      this.setData({ alertPage: 1, alertNoMore: false, alerts: [] })
    }

    try {
      const { alertPage, filterStatus, filterSeverity } = this.data
      const res = await getAlerts({
        page: alertPage,
        page_size: 20,
        status: filterStatus,
        severity: filterSeverity,
      })

      if (res.success) {
        const items = res.data.items || []
        const formatted = items.map(a => this._formatAlert(a))
        const hasMore = res.data.page < res.data.total_pages

        this.setData({
          alerts: refresh ? formatted : [...this.data.alerts, ...formatted],
          alertNoMore: !hasMore,
          alertPage: alertPage + 1,
        })
      }
    } catch (e) {
      console.error('加载告警列表失败:', e)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ alertLoading: false })
    }
  },

  _formatAlert(a) {
    const severityColors = {
      critical: '#ff4d4f',
      high: '#fa8c16',
      medium: '#fadb14',
      low: '#52c41a',
    }
    const severityLabels = {
      critical: '严重',
      high: '高危',
      medium: '中危',
      low: '低危',
    }
    const statusLabels = {
      new: '待处理',
      acknowledged: '已确认',
      resolved: '已解决',
      ignored: '已忽略',
    }
    return {
      ...a,
      severityColor: severityColors[a.severity] || '#999',
      severityLabel: severityLabels[a.severity] || a.severity,
      statusLabel: statusLabels[a.status] || a.status,
      timeText: this._formatRelativeTime(a.created_at),
      titleShort: a.title.length > 30 ? a.title.substring(0, 30) + '...' : a.title,
    }
  },

  onStatusFilterChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({
      statusIndex: idx,
      filterStatus: this.data.statusValues[idx],
      alerts: [],
      alertPage: 1,
      alertNoMore: false,
    })
    this.loadAlerts(true)
  },

  onSeverityFilterChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({
      severityIndex: idx,
      filterSeverity: this.data.severityValues[idx],
      alerts: [],
      alertPage: 1,
      alertNoMore: false,
    })
    this.loadAlerts(true)
  },

  async onAlertTap(e) {
    const id = e.currentTarget.dataset.id
    this.setData({ showDetail: true, detailLoading: true, currentAlert: null })

    try {
      const res = await getAlertDetail(id)
      if (res.success) {
        const a = this._formatAlert(res.data)
        this.setData({ currentAlert: a, detailLoading: false })
      }
    } catch (e) {
      console.error('加载告警详情失败:', e)
      this.setData({ detailLoading: false })
    }
  },

  closeDetail() {
    this.setData({ showDetail: false, currentAlert: null })
  },

  async onAcknowledge() {
    const alert = this.data.currentAlert
    if (!alert) return

    try {
      const res = await acknowledgeAlert(alert.id)
      if (res.success) {
        wx.showToast({ title: '已确认', icon: 'success' })
        this.closeDetail()
        this.loadAlerts(true)
        this.loadAlertStats()
      }
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  async onResolve() {
    const alert = this.data.currentAlert
    if (!alert) return

    try {
      const res = await resolveAlert(alert.id, { resolved_by: 'developer', note: '手动解决' })
      if (res.success) {
        wx.showToast({ title: '已解决', icon: 'success' })
        this.closeDetail()
        this.loadAlerts(true)
        this.loadAlertStats()
      }
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  loadMoreAlerts() {
    if (!this.data.alertNoMore && !this.data.alertLoading) {
      this.loadAlerts(false)
    }
  },

  onAlertScrollToLower() {
    this.loadMoreAlerts()
  },

  // ==================== Tab 1: 系统健康 ====================

  async loadSystemHealth() {
    if (this.data.healthLoading) return
    this.setData({ healthLoading: true })

    try {
      const res = await getSystemHealth()
      if (res.success) {
        this.setData({ healthData: res.data })
      }
    } catch (e) {
      console.error('加载系统健康失败:', e)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ healthLoading: false })
    }
  },

  startHealthPolling() {
    this.stopHealthPolling()
    this.data.healthTimer = setInterval(() => {
      this.loadSystemHealth()
    }, 30000) // 30秒轮询
  },

  stopHealthPolling() {
    if (this.data.healthTimer) {
      clearInterval(this.data.healthTimer)
      this.data.healthTimer = null
    }
  },

  onRefreshHealth() {
    this.loadSystemHealth()
  },

  // ==================== 下拉刷新 ====================

  onPullDownRefresh() {
    if (this.data.activeTab === 0) {
      Promise.all([this.loadAlertStats(), this.loadAlerts(true)])
        .finally(() => wx.stopPullDownRefresh())
    } else if (this.data.activeTab === 1) {
      this.loadSystemHealth().finally(() => wx.stopPullDownRefresh())
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
