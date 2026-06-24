// pages/refund-admin/refund-admin.js
import { API_BASE_URL } from '../../utils/constants.js'
import { getToken } from '../../utils/storage.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    currentTab: 0,
    tabs: [],

    searchPhone: '',
    users: [],
    userPage: 1,
    userHasMore: true,

    appStatusFilter: 'all',
    appPhoneSearch: '',
    applications: [],
    appPage: 1,
    appHasMore: true,
    appLoading: false,

    loading: false,
    // i18n
    // i18n - WXML UI
    tRaTitle: '',
    tRaUserPrefix: '',
    tRaSubtitle: '', tRaSearchPlaceholder: '', tRaSearchBtn: '',
    tRaEnabled: '', tRaDisabled: '', tRaPhonePrefix: '', tRaIdPrefix: '',
    tRaSilver: '', tRaCloseRefund: '', tRaOpenRefund: '',
    tRaSearchHint: '', tRaLoadMore: '',
    tRaAll: '', tRaPending: '', tRaApproved: '', tRaRejected: '',
    tRaAmountLabel: '', tRaTypeLabel: '', tRaReasonLabel: '',
    tRaApplicantLabel: '', tRaTimeLabel: '', tRaProcessTimeLabel: '',
    tRaRejectReasonLabel: '', tRaNoApplications: '',
    tRaTabPermission: '',
    tRaTabApplications: '',
    tRaTabApproved: '',
    tRaNotBound: '',
    tRaVipMember: '',
    tRaNormalUser: '',
    tRaConfirmAction: '',
    tRaConfirmToggle: '',
    tRaEnable: '',
    tRaDisable: '',
    tRaOperationFail: '',
    tRaNetworkFail: '',
    tRaLoadFail: '',
    tRaNoPermission: '',
    tRaRechargeRefund: '',
    tRaMemberRefund: '',
    tRaStatusPending: '',
    tRaStatusApproved: '',
    tRaStatusRejected: ''
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'refundAdmin.title')
    this.loadUsers()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'refundAdmin.title')
      this._updateDynamicLabels()
    })
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tRaTitle: t('refundAdmin.title'),
      tRaUserPrefix: t('refundAdmin.userPrefix'),
      tRaSubtitle: t('refundAdmin.subtitle'), tRaSearchPlaceholder: t('refundAdmin.searchPlaceholder'),
      tRaSearchBtn: t('refundAdmin.searchBtn'), tRaEnabled: t('refundAdmin.enabled'),
      tRaDisabled: t('refundAdmin.disabled'), tRaPhonePrefix: t('refundAdmin.phonePrefix'),
      tRaIdPrefix: t('refundAdmin.idPrefix'), tRaSilver: t('refundAdmin.silverLabel'),
      tRaCloseRefund: t('refundAdmin.closeRefund'), tRaOpenRefund: t('refundAdmin.openRefund'),
      tRaSearchHint: t('refundAdmin.searchUserHint'), tRaLoadMore: t('refundAdmin.loadMore'),
      tRaAll: t('refundAdmin.filterAll'), tRaPending: t('refundAdmin.filterPending'),
      tRaApproved: t('refundAdmin.filterApproved'), tRaRejected: t('refundAdmin.filterRejected'),
      tRaAmountLabel: t('refundAdmin.amountLabel'), tRaTypeLabel: t('refundAdmin.typeLabel'),
      tRaReasonLabel: t('refundAdmin.reasonLabel'), tRaApplicantLabel: t('refundAdmin.applicantLabel'),
      tRaTimeLabel: t('refundAdmin.timeLabel'), tRaProcessTimeLabel: t('refundAdmin.processTimeLabel'),
      tRaRejectReasonLabel: t('refundAdmin.rejectReasonLabel'), tRaNoApplications: t('refundAdmin.noApplications'),
      tRaTabPermission: t('refundAdmin.tabPermission'),
      tRaTabApplications: t('refundAdmin.tabApplications'),
      tRaTabApproved: t('refundAdmin.tabApproved'),
      tRaNotBound: t('refundAdmin.notBound'),
      tRaVipMember: t('refundAdmin.vipMember'),
      tRaNormalUser: t('refundAdmin.normalUser'),
      tRaConfirmAction: t('refundAdmin.confirmAction'),
      tRaConfirmToggle: t('refundAdmin.confirmToggle'),
      tRaEnable: t('refundAdmin.enable'),
      tRaDisable: t('refundAdmin.disable'),
      tRaOperationFail: t('refundAdmin.operationFail'),
      tRaNetworkFail: t('refundAdmin.networkFail'),
      tRaLoadFail: t('refundAdmin.loadFail'),
      tRaNoPermission: t('refundAdmin.noPermission'),
      tRaRechargeRefund: t('refundAdmin.rechargeRefund'),
      tRaMemberRefund: t('refundAdmin.memberRefund'),
      tRaStatusPending: t('refundAdmin.statusPending'),
      tRaStatusApproved: t('refundAdmin.statusApproved'),
      tRaStatusRejected: t('refundAdmin.statusRejected')
    })
  },

  _updateDynamicLabels() {
    this.setData({
      tabs: [this.data.tRaTabPermission, this.data.tRaTabApplications, this.data.tRaTabApproved]
    })
  },

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
            else if (res.statusCode === 403) reject(new Error(this.data.tRaNoPermission))
            else reject(new Error(res.data.error || this.data.tRaLoadFail))
          },
          fail: () => reject(new Error(this.data.tRaNetworkFail))
        })
      })

      const newUsers = (data.users || []).map(u => ({
        ...u,
        totalHairs: (u.scissor_hairs || 0) + (u.comb_hairs || 0),
        displayPhone: u.phone || this.data.tRaNotBound,
        displayName: u.nickname || u.phone || `${app.t('common.unknown')}${u.id}`,
        memberText: u.member_level === 'vip' ? this.data.tRaVipMember : this.data.tRaNormalUser
      }))

      this.setData({
        users: userPage === 1 ? newUsers : [...this.data.users, ...newUsers],
        userHasMore: data.has_more || false
      })
    } catch (e) {
      console.error('加载用户失败:', e)
      wx.showToast({ title: e.message || this.data.tRaLoadFail, icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  async onToggleRefund(e) {
    const userId = e.currentTarget.dataset.userid
    const idx = e.currentTarget.dataset.index
    const user = this.data.users[idx]

    const action = user.refund_enabled ? this.data.tRaDisable : this.data.tRaEnable
    const res = await new Promise(resolve => {
      wx.showModal({
        title: this.data.tRaConfirmAction,
        content: this.data.tRaConfirmToggle.replace('{action}', action).replace('{name}', user.displayName),
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
            else reject(new Error(r.data.error || this.data.tRaOperationFail))
          },
          fail: () => reject(new Error(this.data.tRaNetworkFail))
        })
      })

      wx.showToast({ title: data.message, icon: 'none', duration: 2000 })

      this.setData({
        [`users[${idx}].refund_enabled`]: data.refund_enabled
      })
    } catch (e) {
      console.error('切换退款权限失败:', e)
      wx.showToast({ title: e.message || this.data.tRaOperationFail, icon: 'none' })
    }
  },

  loadMoreUsers() {
    if (this.data.userHasMore && !this.data.loading) {
      this.setData({ userPage: this.data.userPage + 1 })
      this.loadUsers()
    }
  },

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
            else if (res.statusCode === 403) reject(new Error(this.data.tRaNoPermission))
            else reject(new Error(res.data.error || this.data.tRaLoadFail))
          },
          fail: () => reject(new Error(this.data.tRaNetworkFail))
        })
      })

      const newApps = (data.applications || []).map(a => ({
        ...a,
        refundTypeText: a.refund_type === 'recharge' ? this.data.tRaRechargeRefund : this.data.tRaMemberRefund,
        statusText: a.status === 'pending' ? this.data.tRaStatusPending : a.status === 'approved' ? this.data.tRaStatusApproved : this.data.tRaStatusRejected,
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
      wx.showToast({ title: e.message || this.data.tRaLoadFail, icon: 'none' })
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
