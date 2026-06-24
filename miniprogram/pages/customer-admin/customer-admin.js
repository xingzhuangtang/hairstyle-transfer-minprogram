// pages/customer-admin/customer-admin.js
import { getDashboard, getCustomers, searchByPhone, getTodayStats } from '../../api/customer.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    activeTab: 0,
    tabs: ['存量大盘', '客户列表', '精准查询', '今日动态'],

    dashboard: null,

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

    searchPhone: '',
    searchResult: null,
    searchLoading: false,
    searchNotFound: false,
    _searchTimer: null,

    todayStats: null,

    loading: false,
    // i18n
    // i18n - WXML UI
    tCaTitle: '客户档案',
    tCaSubtitle: '开发者端客户数据总览', tCaLoading: '加载中...',
    tCaUserDist: '用户分布', tCaGuest: '游客', tCaNormal: '普通用户', tCaActiveVip: '活跃VIP', tCaExpiredVip: '过期VIP',
    tCaAssetOverview: '资产总览', tCaTotalUsers: '总用户数', tCaCirculationHairs: '流通发丝',
    tCaTotalRecharge: '累计充值', tCaAvgRecharge: '人均充值', tCaNoDashboard: '暂无大盘数据',
    tCaSortLabel: '排序：', tCaLevelLabel: '等级：',
    tCaPhone: '手机号', tCaRechargeAmt: '充值金额', tCaHairsBalance: '发丝余额', tCaLastActive: '最近活跃',
    tCaLoadMore: '加载更多', tCaClickLoadMore: '点击加载更多', tCaNoMore: '没有更多了', tCaNoCustomers: '暂无客户数据',
    tCaSearchPlaceholder: '输入手机号搜索', tCaSearchBtn: '搜索',
    tCaUserType: '用户类型', tCaRegisterTime: '注册时间',
    tCaRecentRecharges: '最近充值记录', tCaRecentConsumptions: '最近消费记录',
    tCaNotFound: '未找到该手机号对应的客户', tCaSearchHint: '输入手机号查询客户详情',
    tCaTodayNew: '今日新增用户', tCaTodayGuest: '游客', tCaTodayRegistered: '注册用户',
    tCaTodayActive: '今日活跃用户', tCaTodayRecharge: '今日充值',
    tCaRechargeAmountLabel: '充值金额', tCaRechargeCount: '充值笔数',
    tCaTodayConsumption: '今日消费', tCaConsumptionCount: '消费笔数', tCaCountUnit: '笔',
    tCaNoTodayStats: '暂无今日动态数据',
    tCaTabDashboard: '存量大盘',
    tCaTabList: '客户列表',
    tCaTabSearch: '精准查询',
    tCaTabToday: '今日动态',
    tCaSortTime: '注册时间',
    tCaSortRecharge: '充值金额',
    tCaSortHairs: '发丝余额',
    tCaSortActive: '最近活跃',
    tCaLevelAll: '全部等级',
    tCaLevelGuest: '游客用户',
    tCaLevelNormal: '普通用户',
    tCaLevelVip: '会员用户',
    tCaLoadFail: '加载失败',
    tCaGuest: '游客',
    tCaVip: '会员',
    tCaNormal: '普通',
    tCaNotBound: '未绑定',
    tCaVipMember: 'VIP会员',
    tCaNormalUser: '普通用户',
    tCaGuestUser: '游客',
    tCaRegisteredUser: '注册用户',
    tCaEnterPhone: '请输入手机号',
    tCaSearchFail: '搜索失败',
    tCaUnknown: '未知',
    tCaJustNow: '刚刚',
    tCaMinutesAgo: '{mins}分钟前',
    tCaHoursAgo: '{hours}小时前',
    tCaDaysAgo: '{days}天前'
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'customerAdmin.title')
    this.loadDashboard()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'customerAdmin.title')
      this._updateDynamicLabels()
    })
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tCaTitle: t('customerAdmin.title'),
      tCaSubtitle: t('customerAdmin.subtitle'), tCaLoading: t('customerAdmin.loadingText'),
      tCaUserDist: t('customerAdmin.userDistribution'), tCaGuest: t('customerAdmin.guestLabel'),
      tCaNormal: t('customerAdmin.normalLabel'), tCaActiveVip: t('customerAdmin.activeVip'),
      tCaExpiredVip: t('customerAdmin.expiredVip'), tCaAssetOverview: t('customerAdmin.assetOverview'),
      tCaTotalUsers: t('customerAdmin.totalUsers'), tCaCirculationHairs: t('customerAdmin.circulationHairs'),
      tCaTotalRecharge: t('customerAdmin.totalRecharge'), tCaAvgRecharge: t('customerAdmin.avgRecharge'),
      tCaNoDashboard: t('customerAdmin.noDashboard'),
      tCaSortLabel: t('customerAdmin.sortLabel'), tCaLevelLabel: t('customerAdmin.levelLabel'),
      tCaPhone: t('customerAdmin.phoneLabel'), tCaRechargeAmt: t('customerAdmin.rechargeAmount'),
      tCaHairsBalance: t('customerAdmin.hairsBalance'), tCaLastActive: t('customerAdmin.lastActive'),
      tCaLoadMore: t('customerAdmin.loadMore'), tCaClickLoadMore: t('customerAdmin.clickLoadMore'),
      tCaNoMore: t('customerAdmin.noMore'), tCaNoCustomers: t('customerAdmin.noCustomers'),
      tCaSearchPlaceholder: t('customerAdmin.searchPlaceholder'), tCaSearchBtn: t('customerAdmin.searchBtn'),
      tCaUserType: t('customerAdmin.userType'), tCaRegisterTime: t('customerAdmin.registerTime'),
      tCaRecentRecharges: t('customerAdmin.recentRecharges'), tCaRecentConsumptions: t('customerAdmin.recentConsumptions'),
      tCaNotFound: t('customerAdmin.notFound'), tCaSearchHint: t('customerAdmin.searchHint'),
      tCaTodayNew: t('customerAdmin.todayNewUsers'), tCaTodayGuest: t('customerAdmin.guestUser'),
      tCaTodayRegistered: t('customerAdmin.registeredUser'),
      tCaTodayActive: t('customerAdmin.todayActive'), tCaTodayRecharge: t('customerAdmin.todayRecharge'),
      tCaRechargeAmountLabel: t('customerAdmin.rechargeAmountLabel'), tCaRechargeCount: t('customerAdmin.rechargeCount'),
      tCaTodayConsumption: t('customerAdmin.todayConsumption'), tCaConsumptionCount: t('customerAdmin.consumptionCount'),
      tCaCountUnit: t('customerAdmin.countUnit'), tCaNoTodayStats: t('customerAdmin.noTodayStats'),
      tCaTabDashboard: t('customerAdmin.tabDashboard'),
      tCaTabList: t('customerAdmin.tabList'),
      tCaTabSearch: t('customerAdmin.tabSearch'),
      tCaTabToday: t('customerAdmin.tabToday'),
      tCaSortTime: t('customerAdmin.sortTime'),
      tCaSortRecharge: t('customerAdmin.sortRecharge'),
      tCaSortHairs: t('customerAdmin.sortHairs'),
      tCaSortActive: t('customerAdmin.sortActive'),
      tCaLevelAll: t('customerAdmin.levelAll'),
      tCaLevelGuest: t('customerAdmin.levelGuest'),
      tCaLevelNormal: t('customerAdmin.levelNormal'),
      tCaLevelVip: t('customerAdmin.levelVip'),
      tCaLoadFail: t('customerAdmin.loadFail'),
      tCaGuest: t('customerAdmin.guest'),
      tCaVip: t('customerAdmin.vip'),
      tCaNormal: t('customerAdmin.normal'),
      tCaNotBound: t('customerAdmin.notBound'),
      tCaVipMember: t('customerAdmin.vipMember'),
      tCaNormalUser: t('customerAdmin.normalUser'),
      tCaGuestUser: t('customerAdmin.guestUser'),
      tCaRegisteredUser: t('customerAdmin.registeredUser'),
      tCaEnterPhone: t('customerAdmin.enterPhone'),
      tCaSearchFail: t('customerAdmin.searchFail'),
      tCaUnknown: t('customerAdmin.unknown'),
      tCaJustNow: t('customerAdmin.justNow'),
      tCaMinutesAgo: t('customerAdmin.minutesAgo'),
      tCaHoursAgo: t('customerAdmin.hoursAgo'),
      tCaDaysAgo: t('customerAdmin.daysAgo')
    })
  },

  _updateDynamicLabels() {
    this.setData({
      tabs: [this.data.tCaTabDashboard, this.data.tCaTabList, this.data.tCaTabSearch, this.data.tCaTabToday],
      sortOptions: [this.data.tCaSortTime, this.data.tCaSortRecharge, this.data.tCaSortHairs, this.data.tCaSortActive],
      levelOptions: [this.data.tCaLevelAll, this.data.tCaLevelGuest, this.data.tCaLevelNormal, this.data.tCaLevelVip]
    })
  },

  onTabChange(e) {
    const tab = parseInt(e.currentTarget.dataset.tab)
    if (tab === this.data.activeTab) return

    this.setData({ activeTab: tab })

    if (tab === 0 && !this.data.dashboard) {
      this.loadDashboard()
    } else if (tab === 1 && this.data.customers.length === 0) {
      this.loadCustomers(true)
    } else if (tab === 3 && !this.data.todayStats) {
      this.loadTodayStats()
    }
  },

  async loadDashboard() {
    if (this.data.loading) return
    this.setData({ loading: true })

    try {
      const res = await getDashboard()
      if (res.success) {
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
        wx.showToast({ title: res.error || this.data.tCaLoadFail, icon: 'none' })
      }
    } catch (e) {
      console.error('加载大盘数据失败:', e)
      wx.showToast({ title: e.error || this.data.tCaLoadFail, icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

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
      wx.showToast({ title: e.error || this.data.tCaLoadFail, icon: 'none' })
    } finally {
      this.setData({ listLoading: false })
    }
  },

  _formatCustomer(c) {
    const totalHairs = (c.scissor_hairs || 0) + (c.comb_hairs || 0)
    let levelText, levelClass
    if (c.user_type === 'guest') {
      levelText = this.data.tCaGuest
      levelClass = 'guest'
    } else if (c.member_level === 'vip') {
      levelText = this.data.tCaVip
      levelClass = 'vip'
    } else {
      levelText = this.data.tCaNormal
      levelClass = 'normal'
    }
    return {
      ...c,
      totalHairs,
      levelText,
      levelClass,
      displayPhone: c.phone || this.data.tCaNotBound,
      displayName: c.nickname || c.phone || `${app.t('common.unknown')}${c.id}`,
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

  onSearchInput(e) {
    const value = e.detail.value
    this.setData({ searchPhone: value })

    if (this.data._searchTimer) {
      clearTimeout(this.data._searchTimer)
    }
  },

  onSearchConfirm() {
    this.onSearch()
  },

  async onSearch() {
    const phone = this.data.searchPhone.trim()
    if (!phone) {
      wx.showToast({ title: this.data.tCaEnterPhone, icon: 'none' })
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
        if (res.id || res.user_id) {
          const formatted = this._formatCustomerDetail(res)
          this.setData({ searchResult: formatted, searchNotFound: false })
        } else {
          this.setData({ searchResult: null, searchNotFound: true })
        }
      }
    } catch (e) {
      console.error('搜索客户失败:', e)
      wx.showToast({ title: e.error || this.data.tCaSearchFail, icon: 'none' })
    } finally {
      this.setData({ searchLoading: false })
    }
  },

  _formatCustomerDetail(u) {
    const totalHairs = (u.scissor_hairs || 0) + (u.comb_hairs || 0)
    const levelText = u.member_level === 'vip' ? this.data.tCaVipMember : this.data.tCaNormalUser
    const typeText = u.user_type === 'guest' ? this.data.tCaGuestUser : this.data.tCaRegisteredUser
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
      displayPhone: u.phone || this.data.tCaNotBound,
      displayName: u.nickname || u.phone || `${app.t('common.unknown')}${u.id}`,
      totalRecharge: (u.total_recharge || 0).toFixed(2),
      createdAtText: this._formatRelativeTime(u.created_at),
      lastActiveText: this._formatRelativeTime(u.last_active_at || u.updated_at),
      recentConsumptions,
      recentRecharges
    }
  },

  async loadTodayStats() {
    if (this.data.loading) return
    this.setData({ loading: true })

    try {
      const res = await getTodayStats()
      if (res.success) {
        const newUsers = res.new_users || {}
        const recharge = res.recharge || {}
        const consumption = res.consumption || {}

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
        wx.showToast({ title: res.error || this.data.tCaLoadFail, icon: 'none' })
      }
    } catch (e) {
      console.error('加载今日动态失败:', e)
      wx.showToast({ title: e.error || this.data.tCaLoadFail, icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onPullDownRefresh() {
    const tab = this.data.activeTab
    let promise

    if (tab === 0) {
      promise = this.loadDashboard()
    } else if (tab === 1) {
      promise = this.loadCustomers(true)
    } else if (tab === 2) {
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

  _formatRelativeTime(timeStr) {
    if (!timeStr) return this.data.tCaUnknown
    const date = new Date(timeStr)
    const now = new Date()
    const diff = now - date
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (seconds < 60) return this.data.tCaJustNow
    if (minutes < 60) return this.data.tCaMinutesAgo.replace('{mins}', String(minutes))
    if (hours < 24) return this.data.tCaHoursAgo.replace('{hours}', String(hours))
    if (days < 30) return this.data.tCaDaysAgo.replace('{days}', String(days))

    const y = date.getFullYear()
    const m = (date.getMonth() + 1).toString().padStart(2, '0')
    const d = date.getDate().toString().padStart(2, '0')
    return `${y}-${m}-${d}`
  }
})
