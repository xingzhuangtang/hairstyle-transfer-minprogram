// pages/consumption/consumption.js
import { API_BASE_URL } from '../../utils/constants.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

// 发丝消费服务类型配置（key only, labels from i18n）
const SERVICE_TYPE_CONFIG = {
  hair_segment: { icon: '✂️' },
  face_merge: { icon: '🔄' },
  sketch: { icon: '🖊️' },
  combined: { icon: '⚡' },
  fm_step: { icon: '🔄' },
  sk_step: { icon: '📝' }
}

// 财务记录类型配置
const FINANCIAL_TYPE_CONFIG = {
  recharge: { icon: '💰', color: '#07c160' },
  member_purchase: { icon: '👑', color: '#ff9900' },
  refund: { icon: '💸', color: '#e64340' },
  commission: { icon: '🎯', color: '#576b95' },
  withdrawal: { icon: '🏦', color: '#fa5151' },
  cash_consumption: { icon: '🛒', color: '#ff6b35' }
}

Page({
  data: {
    activeTab: 'hair',
    hairRecords: [],
    totalHairConsumed: 0,
    hairFilter: 'all',
    hairPage: 1,
    hairNoMore: false,
    moneyRecords: [],
    moneyPage: 1,
    moneyNoMore: false,
    moneyFilter: 'all',
    loading: false,
    pageSize: 20,
    // i18n
    tConsHairTab: '',
    tConsMoneyTab: '',
    tConsTotalConsumed: '',
    tConsumptionCount: '',
    tConsFilterAll: '',
    tConsFilterCombined: '',
    tConsFilterSketch: '',
    tConsFilterFaceMerge: '',
    tConsFilterRecharge: '',
    tConsFilterMember: '',
    tConsFilterRefund: '',
    tConsFilterCommission: '',
    tConsEmptyHair: '',
    tConsEmptyHairTip: '',
    tConsEmptyMoney: '',
    tConsEmptyMoneyTip: '',
    tConsLoadingText: '',
    tConsNoMore: '',
    tConsStatusSuccess: '',
    tConsStatusPending: '',
    tConsStatusFailed: '',
    tConsLoadFail: '',
    tConsNetworkFail: ''
  },

  _serviceTypeNames: {},
  _financialTypeNames: {},
  _statusNames: {},

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'consumption.title')
    this.loadRecords()
  },

  onShow() {
    this._loadI18n()
    app.setNavTitle(this, 'consumption.title')
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tConsHairTab: t('consumption.hairTab'),
      tConsMoneyTab: t('consumption.moneyTab'),
      tConsTotalConsumed: t('consumption.totalConsumed'),
      tConsumptionCount: t('consumption.consumptionCount'),
      tConsFilterAll: t('consumption.filterAll'),
      tConsFilterCombined: t('consumption.filterCombined'),
      tConsFilterSketch: t('consumption.filterSketch'),
      tConsFilterFaceMerge: t('consumption.filterFaceMerge'),
      tConsFilterRecharge: t('consumption.filterRecharge'),
      tConsFilterMember: t('consumption.filterMember'),
      tConsFilterRefund: t('consumption.filterRefund'),
      tConsFilterCommission: t('consumption.filterCommission'),
      tConsEmptyHair: t('consumption.emptyHair'),
      tConsEmptyHairTip: t('consumption.emptyHairTip'),
      tConsEmptyMoney: t('consumption.emptyMoney'),
      tConsEmptyMoneyTip: t('consumption.emptyMoneyTip'),
      tConsLoadingText: t('consumption.loadingText'),
      tConsNoMore: t('consumption.noMore'),
      tConsStatusSuccess: t('consumption.statusSuccess'),
      tConsStatusPending: t('consumption.statusPending'),
      tConsStatusFailed: t('consumption.statusFailed'),
      tConsLoadFail: t('consumption.loadFail'),
      tConsNetworkFail: t('message.networkFail')
    })
    // 更新服务类型名称
    this._serviceTypeNames = {
      hair_segment: t('consumption.serviceHairSegment'),
      face_merge: t('consumption.serviceFaceMerge'),
      sketch: t('consumption.serviceSketch'),
      combined: t('consumption.serviceCombined'),
      fm_step: t('consumption.serviceFmStep'),
      sk_step: t('consumption.serviceSkStep')
    }
    // 更新财务类型名称
    this._financialTypeNames = {
      recharge: t('consumption.typeRecharge'),
      member_purchase: t('consumption.typeMemberPurchase'),
      refund: t('consumption.typeRefund'),
      commission: t('consumption.typeCommission'),
      withdrawal: t('consumption.typeWithdrawal'),
      cash_consumption: t('consumption.typeCashConsumption')
    }
    // 更新状态名称
    this._statusNames = {
      success: t('consumption.statusSuccess'),
      pending: t('consumption.statusPending'),
      failed: t('consumption.statusFailed')
    }
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'consumption.title')
    })
  },

  /**
   * Tab 切换
   */
  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
    this.loadRecords(true)
  },

  /**
   * 加载记录
   */
  async loadRecords(refresh = false) {
    if (this.data.loading) return

    this.setData({ loading: true })

    try {
      const token = app.globalData.token || wx.getStorageSync('token')

      if (this.data.activeTab === 'hair') {
        await this.loadHairRecords(token, refresh)
      } else {
        await this.loadMoneyRecords(token, refresh)
      }
    } catch (e) {
      console.error('加载记录失败:', e)
      wx.showToast({ title: this.data.tConsLoadFail, icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 加载发丝消费记录
   */
  async loadHairRecords(token, refresh) {
    const page = refresh ? 1 : this.data.hairPage

    let url = `${API_BASE_URL}/api/consume/records?page=${page}&page_size=${this.data.pageSize}`
    if (this.data.hairFilter !== 'all') {
      url += `&service_type=${this.data.hairFilter}`
    }

    const res = await this.request(url, token)
    const newRecords = (res.records || []).map(record => this.formatHairRecord(record))

    this.setData({
      hairRecords: refresh ? newRecords : [...this.data.hairRecords, ...newRecords],
      hairNoMore: newRecords.length === 0 || newRecords.length < this.data.pageSize,
      hairPage: page
    })

    this.calculateHairStats()
  },

  /**
   * 加载银两消费记录
   */
  async loadMoneyRecords(token, refresh) {
    const page = refresh ? 1 : this.data.moneyPage

    let url = `${API_BASE_URL}/api/financial/records?page=${page}&page_size=${this.data.pageSize}`
    if (this.data.moneyFilter !== 'all') {
      url += `&record_type=${this.data.moneyFilter}`
    }

    const res = await this.request(url, token)
    const newRecords = (res.records || []).map(record => this.formatMoneyRecord(record))

    this.setData({
      moneyRecords: refresh ? newRecords : [...this.data.moneyRecords, ...newRecords],
      moneyNoMore: newRecords.length === 0 || newRecords.length < this.data.pageSize,
      moneyPage: page
    })
  },

  /**
   * 通用请求方法
   */
  request(url, token) {
    return new Promise((resolve, reject) => {
      wx.request({
        url,
        method: 'GET',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error(res.data.error || this.data.tConsLoadFail))
          }
        },
        fail: (err) => reject(new Error(this.data.tConsNetworkFail))
      })
    })
  },

  /**
   * 格式化发丝消费记录
   */
  formatHairRecord(record) {
    const config = SERVICE_TYPE_CONFIG[record.service_type] || { icon: '❓' }
    return {
      ...record,
      service_name: this._serviceTypeNames[record.service_type] || this._serviceTypeNames['combined'] || '',
      icon: config.icon,
      status_text: this._statusNames[record.status] || '',
      created_at: this.formatTime(record.created_at)
    }
  },

  /**
   * 格式化银两消费记录
   */
  formatMoneyRecord(record) {
    const config = FINANCIAL_TYPE_CONFIG[record.record_type] || { icon: '❓', color: '#999' }
    const amountText = record.amount >= 0 ? `+¥${record.amount}` : `-¥${Math.abs(record.amount)}`

    return {
      ...record,
      type_name: this._financialTypeNames[record.record_type] || '',
      icon: config.icon,
      color: config.color,
      amount_text: amountText,
      status_text: this._statusNames[record.status] || '',
      created_at: this.formatTime(record.created_at)
    }
  },

  /**
   * 计算发丝消费统计
   */
  calculateHairStats() {
    const totalConsumed = this.data.hairRecords.reduce((sum, record) => {
      return sum + (record.hairs_consumed || 0)
    }, 0)

    this.setData({
      totalHairConsumed: totalConsumed
    })
  },

  /**
   * 格式化时间
   */
  formatTime(timeStr) {
    if (!timeStr) return ''
    const date = new Date(timeStr)
    const now = new Date()
    const diff = now - date

    if (diff < 60000) return this.data.tConsJustNow
    if (diff < 3600000) return this.data.tConsMinutesAgo.replace('{m}', String(Math.floor(diff / 60000)))
    if (diff < 86400000) return this.data.tConsHoursAgo.replace('{h}', String(Math.floor(diff / 3600000)))
    if (diff < 604800000) return this.data.tConsDaysAgo.replace('{d}', String(Math.floor(diff / 86400000)))

    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}`
  },

  /**
   * 筛选标签切换
   */
  onFilterChange(e) {
    const type = e.currentTarget.dataset.type
    const tab = this.data.activeTab

    if (tab === 'hair') {
      this.setData({ hairFilter: type, hairPage: 1, hairRecords: [], hairNoMore: false })
    } else {
      this.setData({ moneyFilter: type, moneyPage: 1, moneyRecords: [], moneyNoMore: false })
    }
    this.loadRecords(true)
  },

  /**
   * 滚动到底部加载
   */
  onScrollToLower() {
    if (this.data.loading) return

    const tab = this.data.activeTab
    const noMore = tab === 'hair' ? this.data.hairNoMore : this.data.moneyNoMore

    if (!noMore) {
      if (tab === 'hair') {
        this.setData({ hairPage: this.data.hairPage + 1 })
      } else {
        this.setData({ moneyPage: this.data.moneyPage + 1 })
      }
      this.loadRecords()
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    if (this.data.activeTab === 'hair') {
      this.setData({ hairPage: 1, hairRecords: [], hairNoMore: false })
    } else {
      this.setData({ moneyPage: 1, moneyRecords: [], moneyNoMore: false })
    }
    this.loadRecords(true)
    wx.stopPullDownRefresh()
  }
})
