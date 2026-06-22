// pages/refund-admin/refund-admin.js
import { API_BASE_URL } from '../../utils/constants.js'
import { getToken } from '../../utils/storage.js'

Page({
  data: {
    // Tab 切换
    currentTab: 0,
    tabs: ['退款权限', '申请记录', '成功退款'],

    // Tab 0: 退款权限
    searchPhone: '',
    users: [],
    userPage: 1,
    userHasMore: true,

    // Tab 1 & 2: 申请记录
    appStatusFilter: 'all',
    appPhoneSearch: '',
    applications: [],
    appPage: 1,
    appHasMore: true,
    appLoading: false,

    // 通用
    loading: false
  },

  onLoad() {
    this.loadUsers()
  },

  // ==================== Tab 切换 ====================

  onTabChange(e) {
    const tab = parseInt(e.currentTarget.dataset.tab)
    this.setData({ currentTab: tab })

    if (tab === 0) {
      this.loadUsers()
    } else if (tab === 1) {
      this.loadApplications('all')
    } else if (tab === 2) {
      this.loadApplications('approved')
    }
  },

  // ==================== Tab 0: 退款权限 ====================

  onUserSearchInput(e) {
    this.setData({ searchPhone: e.detail.value })
  },

  onUserSearch() {
    this.setData({
      userPage: 1,
      users: [],
      userHasMore: true
    })
    this.loadUsers()
  },

  async loadUsers() {
    if (this.data.loading) return
    this.setData({ loading: true })

    try {
      const { userPage, searchPhone } = this.data
      const token = getToken()

      const data = await new Promise((resolve, reject) => {
        wx.request({
          url: `${API_BASE_URL}/api/admin/refund/users`,
          method: 'GET',
          data: {
            phone: searchPhone,
            page: userPage,
            page_size: 20
          },
          header: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          success: (res) => {
            if (res.statusCode === 200) resolve(res.data)
            else if (res.statusCode === 403) reject(new Error('无权访问'))
            else reject(new Error(res.data.error || '加载失败'))
          },
          fail: () => reject(new Error('网络请求失败'))
        })
      })

      const newUsers = (data.users || []).map(u => ({
        ...u,
        totalHairs: (u.scissor_hairs || 0) + (u.comb_hairs || 0),
        displayPhone: u.phone || '未绑定',
        displayName: u.nickname || u.phone || `用户${u.id}`,
        memberText: u.member_level === 'vip' ? 'VIP会员' : '普通用户'
      }))

      this.setData({
        users: userPage === 1 ? newUsers : [...this.data.users, ...newUsers],
        userHasMore: data.has_more || false
      })
    } catch (e) {
      console.error('加载用户失败:', e)
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  async onToggleRefund(e) {
    const userId = e.currentTarget.dataset.userid
    const idx = e.currentTarget.dataset.index
    const user = this.data.users[idx]

    const action = user.refund_enabled ? '关闭' : '开通'
    const res = await new Promise(resolve => {
      wx.showModal({
        title: '确认操作',
        content: `确定要${action}用户 ${user.displayName} 的退款权限吗？`,
        success: resolve
      })
    })

    if (!res.confirm) return

    try {
      const token = getToken()
      const data = await new Promise((resolve, reject) => {
        wx.request({
          url: `${API_BASE_URL}/api/admin/refund/toggle`,
          method: 'POST',
          data: { user_id: userId },
          header: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          success: (r) => {
            if (r.statusCode === 200) resolve(r.data)
            else reject(new Error(r.data.error || '操作失败'))
          },
          fail: () => reject(new Error('网络请求失败'))
        })
      })

      wx.showToast({ title: data.message, icon: 'none', duration: 2000 })

      this.setData({
        [`users[${idx}].refund_enabled`]: data.refund_enabled
      })
    } catch (e) {
      console.error('切换退款权限失败:', e)
      wx.showToast({ title: e.message || '操作失败', icon: 'none' })
    }
  },

  loadMoreUsers() {
    if (this.data.userHasMore && !this.data.loading) {
      this.setData({ userPage: this.data.userPage + 1 })
      this.loadUsers()
    }
  },

  // ==================== Tab 1 & 2: 申请记录 ====================

  onAppStatusChange(e) {
    const status = e.currentTarget.dataset.status
    this.setData({
      appStatusFilter: status,
      appPage: 1,
      applications: [],
      appHasMore: true
    })
    this.loadApplications(status)
  },

  onAppPhoneSearchInput(e) {
    this.setData({ appPhoneSearch: e.detail.value })
  },

  onAppPhoneSearch() {
    this.setData({
      appPage: 1,
      applications: [],
      appHasMore: true
    })
    this.loadApplications(this.data.appStatusFilter)
  },

  async loadApplications(status) {
    if (this.data.appLoading) return
    this.setData({ appLoading: true })

    try {
      const { appPage, appPhoneSearch } = this.data
      const token = getToken()

      const data = await new Promise((resolve, reject) => {
        wx.request({
          url: `${API_BASE_URL}/api/admin/refund/applications`,
          method: 'GET',
          data: {
            status: status,
            phone: appPhoneSearch,
            page: appPage,
            page_size: 20
          },
          header: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          success: (res) => {
            if (res.statusCode === 200) resolve(res.data)
            else if (res.statusCode === 403) reject(new Error('无权访问'))
            else reject(new Error(res.data.error || '加载失败'))
          },
          fail: () => reject(new Error('网络请求失败'))
        })
      })

      const newApps = (data.applications || []).map(a => ({
        ...a,
        refundTypeText: a.refund_type === 'recharge' ? '充值退款' : '会员退款',
        statusText: a.status === 'pending' ? '待处理' : a.status === 'approved' ? '已批准' : '已拒绝',
        statusClass: a.status === 'pending' ? 'status-pending' : a.status === 'approved' ? 'status-approved' : 'status-rejected',
        formattedCreatedAt: this.formatTime(a.created_at),
        formattedApprovedAt: a.approved_at ? this.formatTime(a.approved_at) : null
      }))

      this.setData({
        applications: appPage === 1 ? newApps : [...this.data.applications, ...newApps],
        appHasMore: data.has_more || false
      })
    } catch (e) {
      console.error('加载申请记录失败:', e)
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ appLoading: false })
    }
  },

  loadMoreApplications() {
    if (this.data.appHasMore && !this.data.appLoading) {
      this.setData({ appPage: this.data.appPage + 1 })
      this.loadApplications(this.data.appStatusFilter)
    }
  },

  // ==================== 工具方法 ====================

  formatTime(timeStr) {
    if (!timeStr) return ''
    const date = new Date(timeStr)
    return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  },

  onPullDownRefresh() {
    if (this.data.currentTab === 0) {
      this.setData({ userPage: 1, users: [], userHasMore: true })
      this.loadUsers().then(() => wx.stopPullDownRefresh())
    } else {
      this.setData({ appPage: 1, applications: [], appHasMore: true })
      this.loadApplications(this.data.appStatusFilter).then(() => wx.stopPullDownRefresh())
    }
  }
})
