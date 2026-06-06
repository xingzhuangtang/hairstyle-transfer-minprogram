// pages/consumption/consumption.js
import { API_BASE_URL } from '../../utils/constants.js'

// 发丝消费服务类型配置
const SERVICE_TYPE_CONFIG = {
  hair_segment: { name: '发型提取', icon: '✂️' },
  face_merge: { name: '发型融合', icon: '🔄' },
  sketch: { name: '素描转换', icon: '🖊️' },
  combined: { name: '一键生成', icon: '⚡' },
  fm_step: { name: '发型融合-步骤', icon: '🔄' },
  sk_step: { name: '素描转换-步骤', icon: '📝' }
}

// 财务记录类型配置
const FINANCIAL_TYPE_CONFIG = {
  recharge: { name: '充值', icon: '💰', color: '#07c160' },
  member_purchase: { name: '会员购买', icon: '👑', color: '#ff9900' },
  refund: { name: '退款', icon: '💸', color: '#e64340' },
  commission: { name: '推广佣金', icon: '🎯', color: '#576b95' },
  withdrawal: { name: '提现', icon: '🏦', color: '#fa5151' },
  cash_consumption: { name: '存钱罐消费', icon: '🛒', color: '#ff6b35' }
}

// 状态配置
const STATUS_CONFIG = {
  success: '成功',
  pending: '处理中',
  failed: '失败'
}

Page({
  data: {
    activeTab: 'hair', // 'hair' = 发丝消费, 'money' = 银两消费
    // 发丝消费相关
    hairRecords: [],
    totalHairConsumed: 0,
    hairFilter: 'all',
    hairPage: 1,
    hairNoMore: false,
    // 银两消费相关
    moneyRecords: [],
    moneyPage: 1,
    moneyNoMore: false,
    moneyFilter: 'all',
    // 通用
    loading: false,
    pageSize: 20
  },

  onLoad() {
    this.loadRecords()
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
      const app = getApp()
      const token = app.globalData.token || wx.getStorageSync('token')

      if (this.data.activeTab === 'hair') {
        await this.loadHairRecords(token, refresh)
      } else {
        await this.loadMoneyRecords(token, refresh)
      }
    } catch (e) {
      console.error('加载记录失败:', e)
      wx.showToast({ title: '加载失败', icon: 'none' })
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

    // 重新计算统计数据
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
            reject(new Error(res.data.error || '加载失败'))
          }
        },
        fail: (err) => reject(new Error('网络请求失败'))
      })
    })
  },

  /**
   * 格式化发丝消费记录
   */
  formatHairRecord(record) {
    const config = SERVICE_TYPE_CONFIG[record.service_type] || { name: '未知服务', icon: '❓' }
    return {
      ...record,
      service_name: config.name,
      icon: config.icon,
      status_text: STATUS_CONFIG[record.status] || '未知',
      created_at: this.formatTime(record.created_at)
    }
  },

  /**
   * 格式化银两消费记录
   */
  formatMoneyRecord(record) {
    const config = FINANCIAL_TYPE_CONFIG[record.record_type] || { name: '未知类型', icon: '❓', color: '#999' }
    const amountText = record.amount >= 0 ? `+¥${record.amount}` : `-¥${Math.abs(record.amount)}`

    return {
      ...record,
      type_name: config.name,
      icon: config.icon,
      color: config.color,
      amount_text: amountText,
      status_text: STATUS_CONFIG[record.status] || '未知',
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

    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`

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
