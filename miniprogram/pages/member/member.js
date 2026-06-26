// pages/member/member.js
import { getMemberInfo, getMemberOrders, createMemberOrder, payMemberOrder } from '../../api/member.js'
import { getUserInfo } from '../../api/user.js'
import { createVirtualPayOrder, getVirtualPayOrderStatus, requestVirtualPay, getSessionKey, requestWechatPay } from '../../api/payment.js'
import { getVirtualGoodsKey, isIOS } from '../../utils/platform.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    userInfo: {},
    isVip: false,
    remainingDays: 0,
    expireAt: '',
    orders: [],
    // i18n - WXML UI
    tMemberUser: '用户', tMemberWechatUser: '微信用户', tMemberCompanionVip: '陪跑会员', tMemberNormalBadge: '普通用户',
    tMemberDaysLeft: '剩余天数', tMemberExpireTime: '到期时间', tMemberDaysUnit: '天', tMemberPrivileges: '会员特权',
    tMemberPriv50off: '服务 5 折优惠', tMemberPriv50desc: '发型迁移、素描转换等服务享半价',
    tMemberPriv45days: '历史记录保留 45 天', tMemberPriv45desc: '操作记录长期保存，随时查看',
    tMemberPrivGift: '购买即赠 1000 梳子发丝', tMemberPrivGiftDesc: '购买会员即赠送 1000 根梳子发丝',
    tMemberPrivBonus: '充值额外赠送', tMemberPrivBonusDesc: '充值时获得额外梳子发丝奖励',
    tMemberPrivGiftIcon: '赠', tMemberPrivBonusIcon: '充',
    tMemberOpenMember: '开通会员', tMemberPriceUnit: '/年',
    tMemberBuyTip1: '✓ 购买即赠 1000 梳子发丝', tMemberBuyTip2: '✓ 服务 5 折优惠', tMemberBuyTip3: '✓ 历史记录保留 45 天',
    tMemberVirtualPayOpen: '虚拟支付开通', tMemberVirtualPayHint: '通过微信官方虚拟支付完成购买',
    tMemberOrders: '会员订单', tMemberNoOrders: '暂无订单记录', tMemberOrderNo: '订单号：',
    tMemberGiftHairs: '赠送 {hairs} 梳子发丝',
    tMemberRenewTip: '会员即将到期，及时续费继续享受特权',
    tMemberVirtualPayRenew: '虚拟支付续费', tMemberVirtualPayRenewHint: '通过微信官方虚拟支付完成续费',
    // i18n - JS logic
    tMemberConfirmActivate: '确认开通',
    tMemberActivateContent: '开通陪跑会员 ¥99/年，购买即赠 1000 发丝，确认继续？',
    tMemberCreatingOrder: '创建订单中...',
    tMemberCreateOrderFail: '创建订单失败',
    tMemberSimulatedPay: '模拟支付',
    tMemberDevModeContent: '开发者模式：开通会员成功，已赠送 1000 发丝',
    tMemberGetPayParamsFail: '获取虚拟支付参数失败',
    tMemberVirtualPayFail: '调起支付失败',
    tMemberProcessing: '处理中...',
    tMemberPaySuccessMember: '支付成功，会员已开通',
    tMemberPayFailed: '支付失败',
    tMemberPayCancelled: '已取消支付',
    tMemberPayTimeout: '支付处理超时',
    tMemberQueryOrderFail: '查询订单失败',
    tMemberStatusPaid: '已支付',
    tMemberStatusPending: '待支付',
    tMemberStatusFailed: '支付失败',
    tMemberExpired: '已过期',
    tMemberDaysRemaining: '剩余{days}天',
    tMemberHoursRemaining: '剩余{hours}小时'
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'member.title')
    this.loadMemberInfo()
  },

  onShow() {
    this._loadI18n()
    app.setNavTitle(this, 'member.title')
    this.loadMemberInfo()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'member.title')
    })
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tMemberUser: t('member.user'), tMemberWechatUser: t('member.wechatUser'),
      tMemberCompanionVip: t('member.companionVip'), tMemberNormalBadge: t('member.normalBadge'),
      tMemberDaysLeft: t('member.daysLeft'), tMemberExpireTime: t('member.expireTime'),
      tMemberDaysUnit: t('member.daysUnit'), tMemberPrivileges: t('member.privileges'),
      tMemberPriv50off: t('member.priv50off'), tMemberPriv50desc: t('member.priv50desc'),
      tMemberPriv45days: t('member.priv45days'), tMemberPriv45desc: t('member.priv45desc'),
      tMemberPrivGift: t('member.privGiftHairs'), tMemberPrivGiftDesc: t('member.privGiftHairsDesc'),
      tMemberPrivBonus: t('member.privBonus'), tMemberPrivBonusDesc: t('member.privBonusDesc'),
      tMemberPrivGiftIcon: t('member.privGiftIcon'), tMemberPrivBonusIcon: t('member.privBonusIcon'),
      tMemberOpenMember: t('member.openMember'), tMemberPriceUnit: t('member.priceUnit'),
      tMemberBuyTip1: t('member.buyTip1'), tMemberBuyTip2: t('member.buyTip2'), tMemberBuyTip3: t('member.buyTip3'),
      tMemberVirtualPayOpen: t('member.virtualPayOpen'), tMemberVirtualPayHint: t('member.virtualPayHint'),
      tMemberOrders: t('member.memberOrders'), tMemberNoOrders: t('member.noOrders'),
      tMemberOrderNo: t('member.orderNo'), tMemberGiftHairs: t('member.giftHairs'),
      tMemberRenewTip: t('member.renewTip'),
      tMemberVirtualPayRenew: t('member.virtualPayRenew'), tMemberVirtualPayRenewHint: t('member.virtualPayRenewHint'),
      tMemberConfirmActivate: t('member.confirmActivate'),
      tMemberActivateContent: t('member.activateContent'),
      tMemberCreatingOrder: t('member.creatingOrder'),
      tMemberCreateOrderFail: t('member.createOrderFail'),
      tMemberSimulatedPay: t('member.simulatedPay'),
      tMemberDevModeContent: t('member.devModeContent'),
      tMemberGetPayParamsFail: t('member.getPayParamsFail'),
      tMemberVirtualPayFail: t('member.virtualPayFail'),
      tMemberProcessing: t('member.processing'),
      tMemberPaySuccessMember: t('member.paySuccessMember'),
      tMemberPayFailed: t('member.payFailed'),
      tMemberPayCancelled: t('member.payCancelled'),
      tMemberPayTimeout: t('member.payTimeout'),
      tMemberQueryOrderFail: t('member.queryOrderFail'),
      tMemberStatusPaid: t('member.statusPaid'),
      tMemberStatusPending: t('member.statusPending'),
      tMemberStatusFailed: t('member.statusFailed'),
      tMemberExpired: t('member.expired'),
      tMemberDaysRemaining: t('member.daysRemaining'),
      tMemberHoursRemaining: t('member.hoursRemaining')
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
          this.updateCountdown()
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
          bonusText: this.data.tMemberGiftHairs.replace('{hairs}', String(order.bonus_hairs || 0))
        }))
        this.setData({ orders })
      }
    } catch (e) {
      console.error('加载会员订单失败:', e)
    }
  },

  async buyMember() {
    wx.showModal({
      title: this.data.tMemberConfirmActivate,
      content: this.data.tMemberActivateContent,
      success: async (modalRes) => {
        if (modalRes.confirm) {
          try {
            wx.showLoading({ title: this.data.tMemberCreatingOrder })
            await this.handleVirtualPay()
          } catch (e) {
            wx.hideLoading()
            wx.showToast({ title: e.message || this.data.tMemberCreateOrderFail, icon: 'none' })
          }
        }
      }
    })
  },

  async handleVirtualPay() {
    if (isIOS()) {
      await this.handleIOSVirtualPay()
    } else {
      await this.handleAndroidWechatPay()
    }
  },

  async handleIOSVirtualPay() {
    const goodsKey = getVirtualGoodsKey('member', 99)

    const sessionKey = await getSessionKey()

    const orderRes = await createVirtualPayOrder('member', 99, goodsKey, sessionKey)
    if (!orderRes.success) throw new Error(orderRes.error)

    const orderNo = orderRes.order_no
    this.setData({ currentOrderNo: orderNo })

    if (orderRes.is_developer_mode) {
      wx.hideLoading()
      wx.showModal({
        title: this.data.tMemberSimulatedPay,
        content: this.data.tMemberDevModeContent,
        showCancel: false,
        success: () => {
          this.loadMemberInfo()
        }
      })
      return
    }

    wx.hideLoading()

    const payParams = orderRes.virtual_pay_params
    if (!payParams) throw new Error(this.data.tMemberGetPayParamsFail)

    try {
      await requestVirtualPay(payParams)
      this.checkVirtualPayOrderStatus(orderNo)
    } catch (err) {
      console.error('调起虚拟支付失败:', err)
      wx.showToast({
        title: this.data.tMemberVirtualPayFail,
        icon: 'none'
      })
    }
  },

  async handleAndroidWechatPay() {
    const orderRes = await createMemberOrder('wxpay')
    if (!orderRes.success) throw new Error(orderRes.error || this.data.tMemberCreateOrderFail)

    const orderNo = orderRes.order_no
    this.setData({ currentOrderNo: orderNo })

    const payRes = await payMemberOrder(orderNo, 'wxpay')
    if (!payRes.success) throw new Error(payRes.error || this.data.tMemberGetPayParamsFail)

    const payParams = payRes.wxpay_params
    if (!payParams) throw new Error(this.data.tMemberGetPayParamsFail)

    wx.hideLoading()

    try {
      await requestWechatPay(payParams)
      wx.showToast({ title: this.data.tMemberPaySuccessMember, icon: 'success' })
      setTimeout(() => this.loadMemberInfo(), 1500)
    } catch (err) {
      console.error('调起微信支付失败:', err)
      wx.showToast({
        title: this.data.tMemberVirtualPayFail,
        icon: 'none'
      })
    }
  },

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

            wx.showToast({ title: this.data.tMemberPaySuccessMember, icon: 'success' })
            setTimeout(() => this.loadMemberInfo(), 1500)

          } else if (paymentStatus === 'failed' || paymentStatus === 'cancelled') {
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({
              title: paymentStatus === 'failed' ? this.data.tMemberPayFailed : this.data.tMemberPayCancelled,
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
        wx.showToast({ title: this.data.tMemberQueryOrderFail, icon: 'none' })
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
      'success': this.data.tMemberStatusPaid,
      'pending': this.data.tMemberStatusPending,
      'failed': this.data.tMemberStatusFailed
    }
    return map[status] || status
  },

  formatDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
  },

  updateCountdown() {
    if (!this.data.expireAt) return

    const expireDate = new Date(this.data.expireAt)
    const now = new Date()
    const diffMs = expireDate - now

    let countdownText = ''

    if (diffMs <= 0) {
      countdownText = this.data.tMemberExpired
    } else {
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
      const diffDays = Math.floor(diffHours / 24)

      if (diffDays >= 1) {
        countdownText = this.data.tMemberDaysRemaining.replace('{days}', String(diffDays))
      } else {
        countdownText = this.data.tMemberHoursRemaining.replace('{hours}', String(diffHours))
      }
    }

    this.setData({ expireCountdownText: countdownText })
  },

  startCountdownTimer() {
    this.stopCountdownTimer()
    this.updateCountdown()
    this.data.countdownTimer = setInterval(() => {
      this.updateCountdown()
    }, 60 * 60 * 1000)
  },

  stopCountdownTimer() {
    if (this.data.countdownTimer) {
      clearInterval(this.data.countdownTimer)
      this.setData({ countdownTimer: null })
    }
  }
})
