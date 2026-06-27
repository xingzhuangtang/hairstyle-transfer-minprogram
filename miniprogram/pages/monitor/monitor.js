// pages/monitor/monitor.js
import {
  getAlerts, getAlertDetail, acknowledgeAlert, resolveAlert, getAlertStats, getSystemHealth,
  getFixList, executeFix, getFixHistory, getApprovals, approveFix, rejectFix,
  getDefenseRules, runEvolutionAnalysis, getEvolutionReport, getHealthScore,
  verifyAlertResolution, getSimilarBugs,
} from '../../api/monitor.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    activeTab: 0,
    tabs: ['告警', '健康', '修复', '进化'],

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

    showDetail: false,
    currentAlert: null,
    detailLoading: false,

    healthData: null,
    healthLoading: false,
    healthTimer: null,

    fixList: [],
    fixHistory: [],
    approvals: [],
    fixLoading: false,
    fixSubTab: 0,
    fixExecuting: '',

    healthScore: null,
    evolutionReport: null,
    defenseRules: [],
    evolutionLoading: false,
    evolutionSubTab: 0,
    // i18n
    // i18n - WXML UI
    tMonTitle: '系统监控',
    tMonUnknown: '未知',
    tMonSubtitle: '自愈系统 - 感知 / 自愈 / 进化', tMonTotal: '总计', tMonToday: '今日',
    tMonStatusLabel: '状态：', tMonSeverityLabel: '级别：', tMonLoading: '加载中...',
    tMonNoAlerts: '暂无告警记录', tMonClickLoadMore: '点击加载更多',
    tMonSystemRes: '系统资源', tMonMemory: '内存', tMonDisk: '磁盘', tMonProcessMem: '进程内存',
    tMonDatabase: '数据库', tMonConnStatus: '连接状态', tMonNormal: '正常', tMonAbnormal: '异常',
    tMonRespLatency: '响应延迟', tMonMemUsage: '内存使用', tMonHitRate: '命中率',
    tMonAppMetrics: '应用指标', tMonTodayReq: '今日请求数', tMonTodayErr: '今日错误数',
    tMonAvgResp: '平均响应时间', tMonUpdatedAt: '更新于', tMonRefresh: '刷新', tMonNoHealth: '暂无健康数据',
    tMonFixer: '修复器', tMonPendingApproval: '待审批', tMonExecHistory: '执行历史',
    tMonLowRisk: '低风险', tMonMedRisk: '中风险', tMonHighRisk: '高风险',
    tMonExecuting: '执行中...', tMonExecFix: '执行修复', tMonNoFixers: '暂无可用修复器',
    tMonApprove: '批准执行', tMonReject: '拒绝', tMonNoApprovals: '暂无待审批项',
    tMonAuto: '自动', tMonApprovedType: '审批', tMonManual: '手动', tMonNoExecHistory: '暂无执行记录',
    tMonHealthScore: '健康评分', tMonDefenseRules: '防御规则', tMonScoreUnit: '分',
    tMonAlertFreq: '告警频率', tMonFixRate: '修复成功率', tMonSystemMetrics: '系统指标',
    tMonDefCoverage: '防御覆盖率', tMonTodaySummary: '今日告警', tMonWeekSummary: '本周告警',
    tMonWeekFixes: '本周修复', tMonRunAnalysis: '运行进化分析', tMonRiskPred: '风险预测',
    tMonHigh: '高', tMonMed: '中', tMonLow: '低',
    tMonNoDefRules: '暂无防御规则',
    tMonAlertDetail: '告警详情', tMonAlertTitleL: '标题', tMonAlertSevL: '级别', tMonAlertStatL: '状态',
    tMonSourceMod: '来源模块', tMonReqUrl: '请求URL', tMonCreatedAtL: '创建时间',
    tMonDesc: '描述', tMonStack: '堆栈信息', tMonReqParams: '请求参数',
    tMonAcknowledge: '确认', tMonResolve: '解决',
    tMonTabAlerts: '告警',
    tMonTabHealth: '健康',
    tMonTabFix: '修复',
    tMonTabEvolution: '进化',
    tMonStatusAll: '全部状态',
    tMonStatusNew: '待处理',
    tMonStatusAcknowledged: '已确认',
    tMonStatusResolved: '已解决',
    tMonStatusIgnored: '已忽略',
    tMonSeverityAll: '全部级别',
    tMonSeverityCritical: '严重',
    tMonSeverityHigh: '高危',
    tMonSeverityMedium: '中危',
    tMonSeverityLow: '低危',
    tMonLoadFail: '加载失败',
    tMonAcknowledged: '已确认',
    tMonResolved: '已解决',
    tMonOperationFail: '操作失败',
    tMonFixSuccess: '成功',
    tMonFixFailed: '失败',
    tMonFixRunning: '执行中',
    tMonFixSkipped: '跳过',
    tMonRiskLow: '低危',
    tMonRiskMedium: '中危',
    tMonRiskHigh: '高危',
    tMonApprovalPending: '待审批',
    tMonApprovalApproved: '已批准',
    tMonApprovalRejected: '已拒绝',
    tMonApprovalExpired: '已过期',
    tMonConfirmExecute: '确认执行',
    tMonConfirmExecuteContent: '确定执行「{name}」？',
    tMonExecuteSuccess: '执行成功',
    tMonExecuteFail: '执行失败',
    tMonExecuteException: '执行异常',
    tMonApprovedAndExecuted: '已批准并执行',
    tMonRejected: '已拒绝',
    tMonLevelExcellent: '优秀',
    tMonLevelGood: '良好',
    tMonLevelWarning: '警告',
    tMonLevelCritical: '危险',
    tMonActionAutoFix: '自动修复',
    tMonActionWarn: '告警',
    tMonActionSuppress: '抑制',
    tMonAnalysisComplete: '分析完成',
    tMonAnalysisFail: '分析失败',
    tMonUnknown: '未知',
    tMonJustNow: '刚刚',
    tMonMinutesAgo: '{mins}分钟前',
    tMonHoursAgo: '{hours}小时前',
    tMonDaysAgo: '{days}天前',

    // 解法记录弹窗
    showResolveModal: false,
    resolveSubmitting: false,
    resolveForm: {
      category: 'logic',
      severity: 'medium',
      root_cause: '',
      fix_description: '',
      prevention: '',
    },
    bugCategories: ['data_type', 'deployment', 'security', 'performance', 'logic'],
    bugCategoryLabels: ['数据类型', '部署', '安全', '性能', '逻辑'],
    bugCategoryIndex: 4,
    severityLabels: ['低', '中', '高', '严重'],
    severityValues: ['low', 'medium', 'high', 'critical'],
    severityIndex: 1,
    similarBugs: [],

    // 解法记录 i18n
    tMonResolveRecordTitle: '记录修复方案',
    tMonBugCategory: 'Bug 分类',
    tMonSeverity: '严重级别',
    tMonRootCause: '根因分析',
    tMonFixSolution: '修复方案',
    tMonPrevention: '预防措施',
    tMonResolveRecord: '记录并解决',
    tMonResolveSkip: '跳过记录',
    tMonSimilarBugs: '相似历史 Bug',
    tMonVerify: '确认有效',
    tMonReopen: '重新打开',
    tMonVerified: '已验证',
    tMonVerifyFailed: '验证失败',
    tMonVerifyPending: '待验证',
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'monitor.title')
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

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'monitor.title')
      this._updateDynamicLabels()
    })
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tMonTitle: t('monitor.title'),
      tMonUnknown: t('monitor.unknown'),
      tMonSubtitle: t('monitor.subtitle'), tMonTotal: t('monitor.total'), tMonToday: t('monitor.today'),
      tMonStatusLabel: t('monitor.statusLabel'), tMonSeverityLabel: t('monitor.severityLabel'),
      tMonLoading: t('monitor.loadingText'), tMonNoAlerts: t('monitor.noAlerts'),
      tMonClickLoadMore: t('monitor.clickLoadMore'),
      tMonSystemRes: t('monitor.systemResources'), tMonMemory: t('monitor.memory'),
      tMonDisk: t('monitor.disk'), tMonProcessMem: t('monitor.processMemory'),
      tMonDatabase: t('monitor.database'), tMonConnStatus: t('monitor.connectionStatus'),
      tMonNormal: t('monitor.normal'), tMonAbnormal: t('monitor.abnormal'),
      tMonRespLatency: t('monitor.responseLatency'), tMonMemUsage: t('monitor.memoryUsage'),
      tMonHitRate: t('monitor.hitRate'), tMonAppMetrics: t('monitor.appMetrics'),
      tMonTodayReq: t('monitor.todayRequests'), tMonTodayErr: t('monitor.todayErrors'),
      tMonAvgResp: t('monitor.avgResponseTime'), tMonUpdatedAt: t('monitor.updatedAt'),
      tMonRefresh: t('monitor.refresh'), tMonNoHealth: t('monitor.noHealthData'),
      tMonFixer: t('monitor.fixer'), tMonPendingApproval: t('monitor.pendingApproval'),
      tMonExecHistory: t('monitor.execHistory'),
      tMonLowRisk: t('monitor.lowRisk'), tMonMedRisk: t('monitor.mediumRisk'), tMonHighRisk: t('monitor.highRisk'),
      tMonExecuting: t('monitor.executing'), tMonExecFix: t('monitor.executeFix'),
      tMonNoFixers: t('monitor.noFixers'), tMonApprove: t('monitor.approve'), tMonReject: t('monitor.reject'),
      tMonNoApprovals: t('monitor.noApprovals'),
      tMonAuto: t('monitor.auto'), tMonApprovedType: t('monitor.approved'), tMonManual: t('monitor.manual'),
      tMonNoExecHistory: t('monitor.noExecHistory'),
      tMonHealthScore: t('monitor.healthScore'), tMonDefenseRules: t('monitor.defenseRules'),
      tMonScoreUnit: t('monitor.scoreUnit'), tMonAlertFreq: t('monitor.alertFrequency'),
      tMonFixRate: t('monitor.fixSuccessRate'), tMonSystemMetrics: t('monitor.systemMetrics'),
      tMonDefCoverage: t('monitor.defenseCoverage'),
      tMonTodaySummary: t('monitor.todayAlertsSummary'), tMonWeekSummary: t('monitor.weekAlertsSummary'),
      tMonWeekFixes: t('monitor.weekFixesSummary'), tMonRunAnalysis: t('monitor.runAnalysis'),
      tMonRiskPred: t('monitor.riskPrediction'),
      tMonHigh: t('monitor.highRiskLevel'), tMonMed: t('monitor.mediumRiskLevel'), tMonLow: t('monitor.lowRiskLevel'),
      tMonNoDefRules: t('monitor.noDefenseRules'),
      tMonAlertDetail: t('monitor.alertDetail'), tMonAlertTitleL: t('monitor.alertTitle'),
      tMonAlertSevL: t('monitor.alertSeverity'), tMonAlertStatL: t('monitor.alertStatus'),
      tMonSourceMod: t('monitor.sourceModule'), tMonReqUrl: t('monitor.requestUrl'),
      tMonCreatedAtL: t('monitor.createdAt'), tMonDesc: t('monitor.description'),
      tMonStack: t('monitor.stackTrace'), tMonReqParams: t('monitor.requestParams'),
      tMonAcknowledge: t('monitor.acknowledge'), tMonResolve: t('monitor.resolve'),
      tMonTabAlerts: t('monitor.tabAlerts'),
      tMonTabHealth: t('monitor.tabHealth'),
      tMonTabFix: t('monitor.tabFix'),
      tMonTabEvolution: t('monitor.tabEvolution'),
      tMonStatusAll: t('monitor.statusAll'),
      tMonStatusNew: t('monitor.statusNew'),
      tMonStatusAcknowledged: t('monitor.statusAcknowledged'),
      tMonStatusResolved: t('monitor.statusResolved'),
      tMonStatusIgnored: t('monitor.statusIgnored'),
      tMonSeverityAll: t('monitor.severityAll'),
      tMonSeverityCritical: t('monitor.severityCritical'),
      tMonSeverityHigh: t('monitor.severityHigh'),
      tMonSeverityMedium: t('monitor.severityMedium'),
      tMonSeverityLow: t('monitor.severityLow'),
      tMonLoadFail: t('monitor.loadFail'),
      tMonAcknowledged: t('monitor.acknowledged'),
      tMonResolved: t('monitor.resolved'),
      tMonOperationFail: t('monitor.operationFail'),
      tMonFixSuccess: t('monitor.fixSuccess'),
      tMonFixFailed: t('monitor.fixFailed'),
      tMonFixRunning: t('monitor.fixRunning'),
      tMonFixSkipped: t('monitor.fixSkipped'),
      tMonRiskLow: t('monitor.riskLow'),
      tMonRiskMedium: t('monitor.riskMedium'),
      tMonRiskHigh: t('monitor.riskHigh'),
      tMonApprovalPending: t('monitor.approvalPending'),
      tMonApprovalApproved: t('monitor.approvalApproved'),
      tMonApprovalRejected: t('monitor.approvalRejected'),
      tMonApprovalExpired: t('monitor.approvalExpired'),
      tMonConfirmExecute: t('monitor.confirmExecute'),
      tMonConfirmExecuteContent: t('monitor.confirmExecuteContent'),
      tMonExecuteSuccess: t('monitor.executeSuccess'),
      tMonExecuteFail: t('monitor.executeFail'),
      tMonExecuteException: t('monitor.executeException'),
      tMonApprovedAndExecuted: t('monitor.approvedAndExecuted'),
      tMonRejected: t('monitor.rejected'),
      tMonLevelExcellent: t('monitor.levelExcellent'),
      tMonLevelGood: t('monitor.levelGood'),
      tMonLevelWarning: t('monitor.levelWarning'),
      tMonLevelCritical: t('monitor.levelCritical'),
      tMonActionAutoFix: t('monitor.actionAutoFix'),
      tMonActionWarn: t('monitor.actionWarn'),
      tMonActionSuppress: t('monitor.actionSuppress'),
      tMonAnalysisComplete: t('monitor.analysisComplete'),
      tMonAnalysisFail: t('monitor.analysisFail'),
      tMonUnknown: t('monitor.unknown'),
      tMonJustNow: t('monitor.justNow'),
      tMonMinutesAgo: t('monitor.minutesAgo'),
      tMonHoursAgo: t('monitor.hoursAgo'),
      tMonDaysAgo: t('monitor.daysAgo'),
      tMonResolveRecordTitle: t('monitor.resolveRecordTitle'),
      tMonBugCategory: t('monitor.bugCategory'),
      tMonRootCause: t('monitor.rootCause'),
      tMonFixSolution: t('monitor.fixSolution'),
      tMonPrevention: t('monitor.prevention'),
      tMonResolveRecord: t('monitor.resolveRecord'),
      tMonResolveSkip: t('monitor.resolveSkip'),
      tMonSimilarBugs: t('monitor.similarBugs'),
      tMonVerify: t('monitor.verifyResolution'),
      tMonReopen: t('monitor.reopenAlert'),
      tMonVerified: t('monitor.verificationVerified'),
      tMonVerifyFailed: t('monitor.verificationFailed'),
      tMonVerifyPending: t('monitor.verificationPending'),
    })
  },

  _updateDynamicLabels() {
    this.setData({
      tabs: [this.data.tMonTabAlerts, this.data.tMonTabHealth, this.data.tMonTabFix, this.data.tMonTabEvolution],
      statusOptions: [this.data.tMonStatusAll, this.data.tMonStatusNew, this.data.tMonStatusAcknowledged, this.data.tMonStatusResolved, this.data.tMonStatusIgnored],
      severityOptions: [this.data.tMonSeverityAll, this.data.tMonSeverityCritical, this.data.tMonSeverityHigh, this.data.tMonSeverityMedium, this.data.tMonSeverityLow]
    })
  },

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
      wx.showToast({ title: this.data.tMonLoadFail, icon: 'none' })
    } finally {
      this.setData({ alertLoading: false })
    }
  },

  _formatAlert(a) {
    const severityColors = { critical: '#ff4d4f', high: '#fa8c16', medium: '#fadb14', low: '#52c41a' }
    const severityLabels = {
      critical: this.data.tMonSeverityCritical,
      high: this.data.tMonSeverityHigh,
      medium: this.data.tMonSeverityMedium,
      low: this.data.tMonSeverityLow
    }
    const statusLabels = {
      new: this.data.tMonStatusNew,
      acknowledged: this.data.tMonStatusAcknowledged,
      resolved: this.data.tMonStatusResolved,
      ignored: this.data.tMonStatusIgnored
    }
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
        wx.showToast({ title: this.data.tMonAcknowledged, icon: 'success' })
        this.closeDetail(); this.loadAlerts(true); this.loadAlertStats()
      }
    } catch (e) { wx.showToast({ title: this.data.tMonOperationFail, icon: 'none' }) }
  },

  onResolve() {
    const alert = this.data.currentAlert
    if (!alert) return
    this.setData({
      showResolveModal: true,
      resolveForm: { category: 'logic', severity: 'medium', root_cause: '', fix_description: '', prevention: '' },
      bugCategoryIndex: 4,
      severityIndex: 1,
      similarBugs: [],
    })
    this.loadSimilarBugs(alert.id)
  },

  async loadSimilarBugs(alertId) {
    try {
      const res = await getSimilarBugs(alertId)
      if (res.success) this.setData({ similarBugs: res.data || [] })
    } catch (e) { /* ignore */ }
  },

  onCategoryChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({
      bugCategoryIndex: idx,
      'resolveForm.category': this.data.bugCategories[idx],
    })
  },

  onSeverityChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({
      severityIndex: idx,
      'resolveForm.severity': this.data.severityValues[idx],
    })
  },

  onRootCauseInput(e) {
    this.setData({ 'resolveForm.root_cause': e.detail.value })
  },

  onFixSolutionInput(e) {
    this.setData({ 'resolveForm.fix_description': e.detail.value })
  },

  onPreventionInput(e) {
    this.setData({ 'resolveForm.prevention': e.detail.value })
  },

  async submitResolveForm() {
    const alert = this.data.currentAlert
    if (!alert) return
    const form = this.data.resolveForm
    if (!form.root_cause.trim()) {
      wx.showToast({ title: this.data.tMonRootCause + '不能为空', icon: 'none' })
      return
    }
    this.setData({ resolveSubmitting: true })
    try {
      const res = await resolveAlert(alert.id, {
        resolved_by: 'developer',
        note: '手动解决',
        bug_knowledge: {
          category: form.category,
          severity: form.severity,
          root_cause: form.root_cause,
          fix_description: form.fix_description,
          prevention: form.prevention,
        },
      })
      if (res.success) {
        wx.showToast({ title: this.data.tMonResolved, icon: 'success' })
        this.setData({ showResolveModal: false })
        this.closeDetail()
        this.loadAlerts(true)
        this.loadAlertStats()
      }
    } catch (e) {
      wx.showToast({ title: this.data.tMonOperationFail, icon: 'none' })
    } finally {
      this.setData({ resolveSubmitting: false })
    }
  },

  async skipResolve() {
    const alert = this.data.currentAlert
    if (!alert) return
    try {
      const res = await resolveAlert(alert.id, { resolved_by: 'developer', note: '手动解决（跳过记录）' })
      if (res.success) {
        wx.showToast({ title: this.data.tMonResolved, icon: 'success' })
        this.setData({ showResolveModal: false })
        this.closeDetail()
        this.loadAlerts(true)
        this.loadAlertStats()
      }
    } catch (e) {
      wx.showToast({ title: this.data.tMonOperationFail, icon: 'none' })
    }
  },

  closeResolveModal() {
    this.setData({ showResolveModal: false })
  },

  async onVerifyAlert(e) {
    const alert = this.data.currentAlert
    if (!alert) return
    const action = e.currentTarget.dataset.action
    try {
      const res = await verifyAlertResolution(alert.id, { action })
      if (res.success) {
        const label = action === 'verify' ? this.data.tMonVerified : this.data.tMonVerifyFailed
        wx.showToast({ title: label, icon: action === 'verify' ? 'success' : 'none' })
        this.closeDetail()
        this.loadAlerts(true)
        this.loadAlertStats()
      }
    } catch (e) {
      wx.showToast({ title: this.data.tMonOperationFail, icon: 'none' })
    }
  },

  loadMoreAlerts() { if (!this.data.alertNoMore && !this.data.alertLoading) this.loadAlerts(false) },
  onAlertScrollToLower() { this.loadMoreAlerts() },

  async loadSystemHealth() {
    if (this.data.healthLoading) return
    this.setData({ healthLoading: true })
    try {
      const res = await getSystemHealth()
      if (res.success) this.setData({ healthData: res.data })
    } catch (e) {
      wx.showToast({ title: this.data.tMonLoadFail, icon: 'none' })
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
          statusText: {
            success: this.data.tMonFixSuccess,
            failed: this.data.tMonFixFailed,
            running: this.data.tMonFixRunning,
            skipped: this.data.tMonFixSkipped
          }[h.status] || h.status,
          timeText: this._formatRelativeTime(h.executed_at),
        })) : [],
        approvals: approvalRes.success ? (approvalRes.data.items || []).map(a => ({
          ...a,
          riskLabel: {
            low: this.data.tMonRiskLow,
            medium: this.data.tMonRiskMedium,
            high: this.data.tMonRiskHigh
          }[a.risk_level] || a.risk_level,
          statusText: {
            pending: this.data.tMonApprovalPending,
            approved: this.data.tMonApprovalApproved,
            rejected: this.data.tMonApprovalRejected,
            expired: this.data.tMonApprovalExpired
          }[a.status] || a.status,
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
      title: this.data.tMonConfirmExecute,
      content: this.data.tMonConfirmExecuteContent.replace('{name}', fixer ? fixer.name : fixId),
      success: async (res) => {
        if (!res.confirm) return
        this.setData({ fixExecuting: fixId })
        try {
          const result = await executeFix({ fix_id: fixId })
          wx.showToast({ title: result.success ? this.data.tMonExecuteSuccess : this.data.tMonExecuteFail, icon: result.success ? 'success' : 'none' })
          setTimeout(() => this.loadFixData(), 1000)
        } catch (e) {
          wx.showToast({ title: this.data.tMonExecuteException, icon: 'none' })
        } finally { this.setData({ fixExecuting: '' }) }
      }
    })
  },

  async onApproveFix(e) {
    const id = e.currentTarget.dataset.id
    try {
      const res = await approveFix(id)
      wx.showToast({ title: res.success ? this.data.tMonApprovedAndExecuted : this.data.tMonOperationFail, icon: res.success ? 'success' : 'none' })
      setTimeout(() => this.loadFixData(), 1000)
    } catch (e) { wx.showToast({ title: this.data.tMonOperationFail, icon: 'none' }) }
  },

  async onRejectFix(e) {
    const id = e.currentTarget.dataset.id
    try {
      const res = await rejectFix(id)
      wx.showToast({ title: res.success ? this.data.tMonRejected : this.data.tMonOperationFail, icon: res.success ? 'success' : 'none' })
      this.loadFixData()
    } catch (e) { wx.showToast({ title: this.data.tMonOperationFail, icon: 'none' }) }
  },

  onEvolutionSubTabChange(e) {
    this.setData({ evolutionSubTab: parseInt(e.currentTarget.dataset.sub) })
  },

  async loadEvolutionData() {
    this.setData({ evolutionLoading: true })
    try {
      const [scoreRes, rulesRes] = await Promise.all([getHealthScore(), getDefenseRules()])
      const levelLabels = {
        excellent: this.data.tMonLevelExcellent,
        good: this.data.tMonLevelGood,
        warning: this.data.tMonLevelWarning,
        critical: this.data.tMonLevelCritical
      }
      const scoreData = scoreRes.success ? scoreRes.data : null
      if (scoreData) scoreData.levelLabel = levelLabels[scoreData.level] || scoreData.level
      this.setData({
        healthScore: scoreData,
        defenseRules: rulesRes.success ? (rulesRes.data || []).map(r => ({
          ...r,
          actionLabel: {
            auto_fix: this.data.tMonActionAutoFix,
            warn: this.data.tMonActionWarn,
            suppress: this.data.tMonActionSuppress
          }[r.action] || r.action,
          actionColor: { auto_fix: '#52c41a', warn: '#fa8c16', suppress: '#999' }[r.action] || '#999',
          hitText: (this.data.tMonHitCount || '命中 {count} 次').replace('{count}', String(r.hit_count || 0)),
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
        wx.showToast({ title: this.data.tMonAnalysisComplete, icon: 'success' })
      }
    } catch (e) {
      wx.showToast({ title: this.data.tMonAnalysisFail, icon: 'none' })
    } finally { this.setData({ evolutionLoading: false }) }
  },

  async onToggleRule(e) {
    const { id, enabled } = e.currentTarget.dataset
    try {
      const { updateDefenseRule } = await import('../../api/monitor.js')
      await updateDefenseRule(id, { enabled: !enabled })
      this.loadEvolutionData()
    } catch (e) { wx.showToast({ title: this.data.tMonOperationFail, icon: 'none' }) }
  },

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

  _formatRelativeTime(timeStr) {
    if (!timeStr) return this.data.tMonUnknown
    const date = new Date(timeStr)
    const now = new Date()
    const diff = now - date
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)
    if (seconds < 60) return this.data.tMonJustNow
    if (minutes < 60) return this.data.tMonMinutesAgo.replace('{mins}', String(minutes))
    if (hours < 24) return this.data.tMonHoursAgo.replace('{hours}', String(hours))
    if (days < 30) return this.data.tMonDaysAgo.replace('{days}', String(days))
    const y = date.getFullYear()
    const m = (date.getMonth() + 1).toString().padStart(2, '0')
    const d = date.getDate().toString().padStart(2, '0')
    return `${y}-${m}-${d}`
  },
})
