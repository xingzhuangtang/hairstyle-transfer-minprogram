// pages/member/member.js
import { getMemberInfo, buyMember, getMemberOrders, payMemberOrder } from '../../api/member.js'
import { getUserInfo } from '../../api/user.js'
import { createVirtualPayOrder, getVirtualPayOrderStatus } from '../../api/payment.js'
import { needsVirtualPay, getVirtualGoodsKey } from '../../utils/platform.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    userInfo: {},
    isVip: false,
    remainingDays: 0,
    expireAt: '',
    orders: [],
    isVirtualPay: false, // 是否使用虚拟支付（iOS端）
    isDevTools: false,
    currentOrderNo: '',
    // i18n
    tMemberUser: '',
    tMemberWechatUser: '',
    tMemberCompanionVip: '',
    tMemberNormalUser: '',
    tMemberRemainingDays: '',
    tMemberExpireTime: '',
    tMemberDays: '',
    tMemberPrivileges: '',
    tMemberPrivilege1Title: '',
    tMemberPrivilege1Desc: '',
    tMemberPrivilege2Title: '',
    tMemberPrivilege2Desc: '',
    tMemberPrivilege3Title: '',
    tMemberPrivilege3Desc: '',
    tMemberPrivilege4Title: '',
    tMemberPrivilege4Desc: '',
    tMemberOpenMember: '',
    tMemberPricePeriod: '',
    tMemberOpenNow: '',
    tMemberOrders: '',
    tMemberNoOrders: '',
    tMemberOrderNo: '',
    tMemberBonusHairs: '',
    tMemberRenewTip: '',
    tMemberRenewNow: '',
    tMemberConfirmOpen: '',
    tMemberConfirmOpenContent: '',
    tMemberCreatingOrder: '',
    tMemberVirtualPay: '',
    tMemberVirtualPayTip: '',
    tMemberPaySuccess: '',
    tMemberPayFail: '',
    tMemberPayCancel: '',
    tMemberPayTimeout: '',
    tMemberQueryFail: '',
    tMemberOrderPaid: '',
    tMemberOrderPending: '',
    tMemberOrderFailed: '',
    tMemberProcessing: '',
    tMemberLoadFail: ''
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'member.title')
    this.loadMemberInfo()
    this.checkPlatform()
  },

  onShow() {
    this._loadI18n()
    app.setNavTitle(this, 'member.title')
    this.loadMemberInfo()
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tMemberUser: t('member.user'),
      tMemberWechatUser: t('member.wechatUser'),
      tMemberCompanionVip: t('member.companionVip'),
      tMemberNormalUser: t('member.normalUser'),
      tMemberRemainingDays: t('member.remainingDays'),
      tMemberExpireTime: t('member.expireTime'),
      tMemberDays: t('member.days'),
      tMemberPrivileges: t('member.privileges'),
      tMemberPrivilege1Title: t('member.privilege1Title'),
      tMemberPrivilege1Desc: t('member.privilege1Desc'),
      tMemberPrivilege2Title: t('member.privilege2Title'),
      tMemberPrivilege2Desc: t('member.privilege2Desc'),
      tMemberPrivilege3Title: t('member.privilege3Title'),
      tMemberPrivilege3Desc: t('member.privilege3Desc'),
      tMemberPrivilege4Title: t('member.privilege4Title'),
      tMemberPrivilege4Desc: t('member.privilege4Desc'),
      tMemberOpenMember: t('member.openMember'),
      tMemberPricePeriod: t('member.price'),
      tMemberOpenNow: t('member.openNow'),
      tMemberOrders: t('member.memberOrders'),
      tMemberNoOrders: t('member.noOrders'),
      tMemberOrderNo: t('member.orderNo'),
      tMemberBonusHairs: t('member.bonusHairs'),
      tMemberRenewTip: t('member.renewTip'),
      tMemberRenewNow: t('member.renewNow'),
      tMemberConfirmOpen: t('member.confirmOpen'),
      tMemberConfirmOpenContent: t('member.confirmOpenContent'),
      tMemberCreatingOrder: t('balance.creatingOrder'),
      tMemberVirtualPay: t('balance.virtualPay'),
      tMemberVirtualPayTip: t('balance.virtualPayTip'),
      tMemberPaySuccess: t('balance.paySuccess'),
      tMemberPayFail: t('balance.payFail'),
      tMemberPayCancel: t('balance.payCancel'),
      tMemberPayTimeout: t('balance.payTimeout'),
      tMemberQueryFail: t('balance.queryFail'),
      tMemberOrderPaid: t('member.orderPaid'),
      tMemberOrderPending: t('member.orderPending'),
      tMemberOrderFailed: t('member.orderFailed'),
      tMemberProcessing: t('balance.processing'),
      tMemberLoadFail: t('common.loadFail')
    })
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'member.title')
    })
  },

  /**
   * 检测当前平台
   */
  async checkPlatform() {
    const isVirtual = needsVirtualPay()
    const systemInfo = wx.getSystemInfoSync()
    const isDev = systemInfo.platform === 'devtools'

    this.setData({
      isVirtualPay: isVirtual,
      isDevTools: isDev
    })

    console.log('会员页平台检测:', {
      platform: systemInfo.platform,
      isVirtualPay: isVirtual,
      isDevTools: isDev
    })
  },

  async loadMemberInfo() {
    try {
      const userRes = await getUserInfo()
      if (userRes.success) {
        this.setData({ userInfo: userRes.user || {} })
      }

      const memberRes = await getMemberInfo()
      if (memberRes.success || memberRes.is_vip !== undefined) {
        const isVip = memberRes.is_vip || false
        const remainingDays = memberRes.remaining_days || 0
        const expireAt = memberRes.expire_at ? this.formatDate(memberRes.expire_at) : ''

        this.setData({ isVip, remainingDays, expireAt })

        if (isVip) {
          this.loadMemberOrders()
        }
      }
    } catch (e) {
      console.error('加载会员信息失败:', e)
    }
  },

  async loadMemberOrders() {
    try {
      const res = await getMemberOrders(1, 10)
      if (res.success) {
        const orders = res.orders.map(order => ({
          ...order,
          payment_status_text: this.getPaymentStatusText(order.payment_status),
          created_at: this.formatDate(order.created_at),
          bonus_hairs_text: this.data.tMemberBonusHairs.replace('{hairs}', String(order.bonus_hairs || 0))
        }))
        this.setData({ orders })
      }
    } catch (e) {
      console.error('加载会员订单失败:', e)
    }
  },

  async buyMember() {
    wx.showModal({
      title: this.data.tMemberConfirmOpen,
      content: this.data.tMemberConfirmOpenContent,
      success: async (modalRes) => {
        if (modalRes.confirm) {
          try {
            wx.showLoading({ title: this.data.tMemberCreatingOrder })

            // iOS端使用虚拟支付
            if (this.data.isVirtualPay || this.data.isDevTools) {
              await this.handleVirtualPay()
            } else {
              // Android端使用普通微信支付
              await this.handleNormalPay()
            }
          } catch (e) {
            wx.hideLoading()
            wx.showToast({ title: e.message || this.data.tMemberPayFail, icon: 'none' })
          }
        }
      }
    })
  },

  /**
   * 处理普通微信支付（Android端）
   */
  async handleNormalPay() {
    const orderRes = await buyMember('wechat')
    if (!orderRes.success) throw new Error(orderRes.error)

    const orderNo = orderRes.order_no
    this.setData({ currentOrderNo: orderNo })
    wx.hideLoading()
    await this.handleWechatPay(orderNo)
  },

  /**
   * 处理微信虚拟支付（iOS端）
   */
  async handleVirtualPay() {
    const goodsKey = getVirtualGoodsKey('member', 99)
    const orderRes = await createVirtualPayOrder('member', 99, goodsKey)
    if (!orderRes.success) throw new Error(orderRes.error)

    const orderNo = orderRes.order_no
    this.setData({ currentOrderNo: orderNo })
    wx.hideLoading()

    wx.showModal({
      title: this.data.tMemberVirtualPay,
      content: this.data.tMemberVirtualPayTip + ' ¥99',
      showCancel: false,
      success: () => {
        this.checkVirtualPayOrderStatus(orderNo)
      }
    })
  },

  async handleWechatPay(orderNo) {
    try {
      const payRes = await payMemberOrder(orderNo, 'wechat')
      if (!payRes.success) throw new Error(payRes.error)

      // 调起微信支付
      wx.requestPayment({
        ...payRes.wxpay_params,
        total_fee: payRes.wxpay_params.total_fee || 0,
        success: () => {
          wx.showToast({ title: this.data.tMemberPaySuccess, icon: 'success' })
          setTimeout(() => this.loadMemberInfo(), 1500)
        },
        fail: (err) => {
          wx.showToast({
            title: err.errMsg.includes('cancel') ? this.data.tMemberPayCancel : this.data.tMemberPayFail,
            icon: 'none'
          })
        }
      })
    } catch (e) {
      wx.showToast({ title: e.message || this.data.tMemberPayFail, icon: 'none' })
    }
  },

  /**
   * 查询虚拟支付订单状态（iOS端）
   */
  async checkVirtualPayOrderStatus(orderNo) {
    wx.showLoading({ title: this.data.tMemberProcessing })

    let count = 0
    const maxCount = 15
    const timer = setInterval(async () => {
      count++

      try {
        const res = await getVirtualPayOrderStatus(orderNo)

        if (res.success) {
          const paymentStatus = res.payment_status

          if (paymentStatus === 'success') {
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({ title: this.data.tMemberOrderPaid, icon: 'success' })
            setTimeout(() => this.loadMemberInfo(), 1500)

          } else if (paymentStatus === 'failed' || paymentStatus === 'cancelled') {
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({
              title: paymentStatus === 'failed' ? this.data.tMemberOrderFailed : this.data.tMemberPayCancel,
              icon: 'none'
            })

          } else if (count >= maxCount) {
            clearInterval(timer)
            wx.hideLoading()
            wx.showToast({ title: this.data.tMemberPayTimeout, icon: 'none' })
          }
        }

      } catch (e) {
        clearInterval(timer)
        wx.hideLoading()
        console.error('查询虚拟支付订单状态失败:', e)
        wx.showToast({ title: this.data.tMemberQueryFail, icon: 'none' })
      }
    }, 2000)

    setTimeout(() => {
      clearInterval(timer)
      wx.hideLoading()
    }, 30000)
  },

  renewMember() {
    this.buyMember()
  },

  getPaymentStatusText(status) {
    const map = {
      'success': this.data.tMemberOrderPaid,
      'pending': this.data.tMemberOrderPending,
      'failed': this.data.tMemberOrderFailed
    }
    return map[status] || status
  },

  formatDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
  }
})
