// pages/History/history.js
import { getMemberInfo } from '../../api/member.js'
import { getHistoryRecords } from '../../api/hair.js'

// 服务类型映射
const SERVICE_TYPE_MAP = {
  hair_segment: '发型提取',
  face_merge: '发型融合',
  sketch: '素描转换',
  combined: '一键生成',
  fm_step: '融合步骤',
  sk_step: '素描步骤'
}

Page({
  data: {
    isVip: false,
    remainingDays: 0,
    records: [],
    loading: false,
    page: 1,
    pageSize: 20,
    hasMore: true
  },

  onLoad() {
    this.loadMemberInfo()
  },

  onShow() {
    this.loadMemberInfo()
  },

  async loadMemberInfo() {
    try {
      const res = await getMemberInfo()
      if (res.success || res.is_vip !== undefined) {
        const isVip = res.is_vip || false
        const remainingDays = res.remaining_days || 0

        this.setData({ isVip, remainingDays })

        if (isVip) {
          this.loadHistoryRecords()
        }
      }
    } catch (e) {
      console.error('加载会员信息失败:', e)
    }
  },

  async loadHistoryRecords(refresh = false) {
    if (this.data.loading) return

    const currentPage = refresh ? 1 : this.data.page

    try {
      this.setData({ loading: true })

      const res = await getHistoryRecords(currentPage, this.data.pageSize)

      if (res.success) {
        const newRecords = res.records.map(record => ({
          ...record,
          id: record.id,
          result_image: record.result_image || record.result_url || '',
          service_type: record.service_type || 'combined',
          service_type_text: SERVICE_TYPE_MAP[record.service_type] || '发型迁移',
          is_expired: record.is_expired || false,
          created_at: this.formatDate(record.created_at)
        }))

        this.setData({
          records: refresh ? newRecords : [...this.data.records, ...newRecords],
          page: currentPage + 1,
          hasMore: res.records.length === this.data.pageSize,
          loading: false
        })
      } else {
        this.setData({ loading: false })
      }
    } catch (e) {
      console.error('加载历史记录失败:', e)
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  loadMore() {
    if (!this.data.hasMore && !this.data.loading) {
      wx.showToast({ title: '没有更多了', icon: 'none' })
      return
    }
    this.loadHistoryRecords(false)
  },

  viewDetail(e) {
    const recordId = e.currentTarget.dataset.id
    const record = this.data.records.find(r => r.id === recordId)
    if (!record) return
    
    if (record.is_expired) {
      wx.showToast({ title: '记录已过期', icon: 'none' })
      return
    }

    // 预览结果图片
    if (record.result_image) {
      wx.previewImage({
        urls: [record.result_image],
        current: record.result_image
      })
    } else {
      wx.showToast({ title: '暂无结果图片', icon: 'none' })
    }
  },

  onImageError(e) {
    const index = e.currentTarget.dataset.index
    const records = this.data.records
    if (records[index]) {
      records[index].result_image = '/images/empty-device.svg'
      this.setData({ records })
    }
  },

  goToMember() {
    wx.switchTab({ url: '/pages/profile/profile' })
  },

  formatDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hour = String(d.getHours()).padStart(2, '0')
    const minute = String(d.getMinutes()).padStart(2, '0')
    return `${year}-${month}-${day} ${hour}:${minute}`
  }
})
