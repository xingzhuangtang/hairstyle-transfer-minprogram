// pages/customer-admin/customer-admin.js
import { getDashboard, getCustomers, searchByPhone, getTodayStats } from '../../api/customer.js'

Page({
  data: {
    activeTab: 0,  // 0:大盘 1:列表 2:搜索 3:今日动态
    tabs: ['存量大盘', '客户列表', '精准查询', '今日动态'],

    // Tab 0: 大盘数据
    dashboard: null,

    // Tab 1: 列表数据
    customers: [],
    listLoading: false,
    listPage: 1,
    listNoMore: false,
    sortBy: 'created_at_desc',
    filterLevel: '',
    filterType: '',
    sortOptions: ['注册时间', '充值金额', '发丝余额', '最近活跃'],
    sortValues: ['created_at_desc', 'recharge_desc', 'hairs_desc', 'last_active'],
    sortIndex: 0,
    levelOptions: ['全部等级', '游客用户', '普通用户', '会员用户'],
    levelValues: ['', 'guest', 'normal', 'vip'],
    levelIndex: 0,

    // Tab 2: 搜索数据
    searchPhone: '',
    searchResult: null,
    searchLoading: false,
    searchNotFound: false,
    _searchTimer: null,

    // Tab 3: 今日动态
    todayStats: null,

    // 通用
    loading: false
  },

  onLoad() {
    this.loadDashboard()
  },

  // ==================== Tab 切换 ====================

  onTabChange(e) {
    const tab = parseInt(e.currentTarget.dataset.tab)
    if (tab === this.data.activeTab) return

    this.setData({ activeTab: tab })

    // 懒加载：切换 Tab 时才请求数据
    if (tab === 0 && !this.data.dashboard) {
      this.loadDashboard()
    } else if (tab === 1 && this.data.customers.length === 0) {
      this.loadCustomers(true)
    } else if (tab === 3 && !this.data.todayStats) {
      this.loadTodayStats()
    }
  },

  // ==================== Tab 0: 存量大盘 ====================

  async loadDashboard() {
    if (this.data.loading) return
    this.setData({ loading: true })

    try {
      const res = await getDashboard()
      if (res.success) {
        // 后端返回：user_distribution, overview
        const distribution = res.user_distribution || {}
        const overview = res.overview || {}
        const total = overview.total_users || 0

        const guestPct = total > 0 ? ((distribution.guest || 0) / total * 100).toFixed(1) : '0.0'
        const normalPct = total > 0 ? ((distribution.normal || 0) / total * 100).toFixed(1) : '0.0'
        const activeVipPct = total > 0 ? ((distribution.vip_active || 0) / total * 100).toFixed(1) : '0.0'
        const expiredVipPct = total > 0 ? ((distribution.vip_expired || 0) / total * 100).toFixed(1) : '0.0'

        this.setData({
          dashboard: {
            totalUsers: total,
            circulationHairs: overview.total_hairs || 0,
            totalRecharge: (overview.total_recharge || 0).toFixed(2),
            avgRecharge: (overview.avg_recharge || 0).toFixed(2),
            distribution: {
              guest: distribution.guest || 0,
              normal: distribution.normal || 0,
              activeVip: distribution.vip_active || 0,
              expiredVip: distribution.vip_expired || 0
            },
            guestPct,
            normalPct,
            activeVipPct,
            expiredVipPct
          }
        })
      } else {
        wx.showToast({ title: res.error || '加载失败', icon: 'none' })
      }
    } catch (e) {
      console.error('加载大盘数据失败:', e)
      wx.showToast({ title: e.error || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  // ==================== Tab 1: 客户列表 ====================

  onSortChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({
      sortIndex: idx,
      sortBy: this.data.sortValues[idx],
      customers: [],
      listPage: 1,
      listNoMore: false
    })
    this.loadCustomers(true)
  },

  onLevelFilterChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({
      levelIndex: idx,
      filterLevel: this.data.levelValues[idx],
      customers: [],
      listPage: 1,
      listNoMore: false
    })
    this.loadCustomers(true)
  },

  async loadCustomers(refresh = false) {
    if (this.data.listLoading) return
    this.setData({ listLoading: true })

    if (refresh) {
      this.setData({ listPage: 1, listNoMore: false, customers: [] })
    }

    try {
      const { listPage, sortBy, filterLevel } = this.data
      const res = await getCustomers({
        page: listPage,
        page_size: 20,
        sort_by: sortBy,
        level: filterLevel
      })

      const list = (res.data && res.data.items) || res.customers || res.users || []
      const formatted = list.map(c => this._formatCustomer(c))
      const hasMore = (res.data && res.data.page < res.data.total_pages) || res.has_more || false

      this.setData({
        customers: refresh ? formatted : [...this.data.customers, ...formatted],
        listNoMore: !hasMore,
        listPage: listPage + 1
      })
    } catch (e) {
      console.error('加载客户列表失败:', e)
      wx.showToast({ title: e.error || '加载失败', icon: 'none' })
    } finally {
      this.setData({ listLoading: false })
    }
  },

  _formatCustomer(c) {
    const totalHairs = (c.scissor_hairs || 0) + (c.comb_hairs || 0)
    let levelText, levelClass
    if (c.user_type === 'guest') {
      levelText = '游客'
      levelClass = 'guest'
    } else if (c.member_level === 'vip') {
      levelText = '会员'
      levelClass = 'vip'
    } else {
      levelText = '普通'
      levelClass = 'normal'
    }
    return {
      ...c,
      totalHairs,
      levelText,
      levelClass,
      displayPhone: c.phone || '未绑定',
      displayName: c.nickname || c.phone || `用户${c.id}`,
      totalRecharge: (c.total_recharge || 0).toFixed(2),
      lastActiveText: this._formatRelativeTime(c.last_active_at || c.updated_at)
    }
  },

  loadMoreCustomers() {
    if (!this.data.listNoMore && !this.data.listLoading) {
      this.loadCustomers(false)
    }
  },

  onListScrollToLower() {
    this.loadMoreCustomers()
  },

  // ==================== Tab 2: 精准查询 ====================

  onSearchInput(e) {
    const value = e.detail.value
    this.setData({ searchPhone: value })

    // 防抖 300ms
    if (this.data._searchTimer) {
      clearTimeout(this.data._searchTimer)
    }
    // 不在这里自动搜索，用户需要点按钮或按确认
  },

  onSearchConfirm() {
    this.onSearch()
  },

  async onSearch() {
    const phone = this.data.searchPhone.trim()
    if (!phone) {
      wx.showToast({ title: '请输入手机号', icon: 'none' })
      return
    }

    this.setData({ searchLoading: true, searchResult: null, searchNotFound: false })

    try {
      const res = await searchByPhone(phone)
      if (res.success && (res.user || res.customer)) {
        const user = res.user || res.customer
        const formatted = this._formatCustomerDetail(user)
        this.setData({ searchResult: formatted, searchNotFound: false })
      } else if (res.user === null || res.customer === null || res.not_found) {
        this.setData({ searchResult: null, searchNotFound: true })
      } else {
        // 尝试直接作为用户数据处理
        if (res.id || res.user_id) {
          const formatted = this._formatCustomerDetail(res)
          this.setData({ searchResult: formatted, searchNotFound: false })
        } else {
          this.setData({ searchResult: null, searchNotFound: true })
        }
      }
    } catch (e) {
      console.error('搜索客户失败:', e)
      wx.showToast({ title: e.error || '搜索失败', icon: 'none' })
    } finally {
      this.setData({ searchLoading: false })
    }
  },

  _formatCustomerDetail(u) {
    const totalHairs = (u.scissor_hairs || 0) + (u.comb_hairs || 0)
    const levelText = u.member_level === 'vip' ? 'VIP会员' : '普通用户'
    const typeText = u.user_type === 'guest' ? '游客' : '注册用户'
    const recentConsumptions = (u.recent_consumptions || []).map(c => ({
      ...c,
      amountText: (c.amount || 0).toFixed(2),
      timeText: this._formatRelativeTime(c.created_at)
    }))
    const recentRecharges = (u.recent_recharges || []).map(r => ({
      ...r,
      amountText: (r.amount || 0).toFixed(2),
      timeText: this._formatRelativeTime(r.created_at)
    }))
    return {
      ...u,
      totalHairs,
      levelText,
      typeText,
      displayPhone: u.phone || '未绑定',
      displayName: u.nickname || u.phone || `用户${u.id}`,
      totalRecharge: (u.total_recharge || 0).toFixed(2),
      createdAtText: this._formatRelativeTime(u.created_at),
      lastActiveText: this._formatRelativeTime(u.last_active_at || u.updated_at),
      recentConsumptions,
      recentRecharges
    }
  },

  // ==================== Tab 3: 今日动态 ====================

  async loadTodayStats() {
    if (this.data.loading) return
    this.setData({ loading: true })

    try {
      const res = await getTodayStats()
      if (res.success) {
        // 后端返回：new_users, active_users, recharge, consumption
        const newUsers = res.new_users || {}
        const recharge = res.recharge || {}
        const consumption = res.consumption || {}

        // 转换 consumption.by_service_type 为数组格式
        const byServiceType = consumption.by_service_type || {}
        const consumptionByService = Object.keys(byServiceType).map(key => ({
          service: key,
          count: byServiceType[key]
        }))

        this.setData({
          todayStats: {
            newUsers: newUsers.total || 0,
            newGuests: newUsers.guest || 0,
            newRegistered: newUsers.normal || 0,
            newVip: newUsers.vip || 0,
            activeUsers: res.active_users || 0,
            rechargeAmount: (recharge.amount || 0).toFixed(2),
            rechargeCount: recharge.count || 0,
            consumptionCount: consumption.total || 0,
            consumptionByService
          }
        })
      } else {
        wx.showToast({ title: res.error || '加载失败', icon: 'none' })
      }
    } catch (e) {
      console.error('加载今日动态失败:', e)
      wx.showToast({ title: e.error || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  // ==================== 下拉刷新 ====================

  onPullDownRefresh() {
    const tab = this.data.activeTab
    let promise

    if (tab === 0) {
      promise = this.loadDashboard()
    } else if (tab === 1) {
      promise = this.loadCustomers(true)
    } else if (tab === 2) {
      // 搜索页不自动刷新，保持当前结果
      promise = Promise.resolve()
    } else if (tab === 3) {
      promise = this.loadTodayStats()
    }

    if (promise) {
      promise.finally(() => wx.stopPullDownRefresh())
    } else {
      wx.stopPullDownRefresh()
    }
  },

  // ==================== 工具方法 ====================

  /**
   * 格式化为相对时间
   */
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

    // 超过 30 天显示具体日期
    const y = date.getFullYear()
    const m = (date.getMonth() + 1).toString().padStart(2, '0')
    const d = date.getDate().toString().padStart(2, '0')
    return `${y}-${m}-${d}`
  }
})
