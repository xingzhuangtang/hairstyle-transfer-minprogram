// pages/consumption/consumption.js
import { API_BASE_URL } from '../../utils/constants.js'

// 服务类型配置
const SERVICE_TYPE_CONFIG = {
  hair_segment: { name: '发型提取', icon: '✂️' },
  face_merge: { name: '发型融合', icon: '' },
  sketch: { name: '素描转换', icon: '🖊️' },
  combined: { name: '一键生成', icon: '⚡' },
  fm_step: { name: '发型融合-步骤', icon: '🔄' },
  sk_step: { name: '素描转换-步骤', icon: '📝' }
}

// 状态配置
const STATUS_CONFIG = {
  success: '成功',
  failed: '失败'
}

Page({
  data: {
    records: [],
    totalConsumed: 0,
    totalCount: 0,
    activeFilter: 'all',
    page: 1,
    pageSize: 20,
    loading: false,
    noMore: false
  },

  onLoad() {
    this.loadConsumptionRecords()
  },

  /**
   * 加载消费记录
   */
  async loadConsumptionRecords(refresh = false) {
    if (this.data.loading) return

    this.setData({ loading: true })

    try {
      const app = getApp()
      const token = app.globalData.token || wx.getStorageSync('token')

      let url = `${API_BASE_URL}/api/consume/records?page=${this.data.page}&page_size=${this.data.pageSize}`
      if (this.data.activeFilter !== 'all') {
        url += `&service_type=${this.data.activeFilter}`
      }

      const res = await new Promise((resolve, reject) => {
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

      const newRecords = (res.records || []).map(record => this.formatRecord(record))

      this.setData({
        records: refresh ? newRecords : [...this.data.records, ...newRecords],
        loading: false,
        noMore: newRecords.length === 0 || newRecords.length < this.data.pageSize
      })

      // 重新计算统计数据
      this.calculateStats()
    } catch (e) {
      console.error('加载消费记录失败:', e)
      this.setData({ loading: false })
      if (this.data.records.length === 0) {
        wx.showToast({ title: e.message || '加载失败', icon: 'none' })
      }
    }
  },

  /**
   * 加载统计数据（本地计算）
   */
  calculateStats() {
    const totalConsumed = this.data.records.reduce((sum, record) => {
      return sum + (record.hairs_consumed || 0)
    }, 0)

    this.setData({
      totalConsumed,
      totalCount: this.data.records.length
    })
  },

  /**
   * 格式化记录数据
   */
  formatRecord(record) {
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
   * 格式化时间
   */
  formatTime(timeStr) {
    if (!timeStr) return ''
    const date = new Date(timeStr)
    const now = new Date()
    const diff = now - date

    // 小于 1 分钟
    if (diff < 60000) {
      return '刚刚'
    }
    // 小于 1 小时
    if (diff < 3600000) {
      return `${Math.floor(diff / 60000)}分钟前`
    }
    // 小于 24 小时
    if (diff < 86400000) {
      return `${Math.floor(diff / 3600000)}小时前`
    }
    // 小于 7 天
    if (diff < 604800000) {
      return `${Math.floor(diff / 86400000)}天前`
    }

    // 超过 7 天，显示具体日期
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
    this.setData({
      activeFilter: type,
      page: 1,
      records: [],
      noMore: false
    })
    this.loadConsumptionRecords(true)
  },

  /**
   * 滚动到底部加载
   */
  onScrollToLower() {
    if (!this.data.noMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 })
      this.loadConsumptionRecords()
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    this.setData({ page: 1, records: [], noMore: false })
    this.loadConsumptionRecords(true)
    wx.stopPullDownRefresh()
  }
})
