// pages/balance/balance.js
import { getUserInfo } from '../../api/user.js'
import { createVirtualPayOrder, getVirtualPayOrderStatus, requestVirtualPay, getSessionKey, createWechatPayOrder, payRechargeOrder, requestWechatPay } from '../../api/payment.js'
import { getVirtualGoodsKey, isIOS } from '../../utils/platform.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    scissorHairs: 0,
    combHairs: 0,
    totalHairs: 0,
    selectedAmount: null,
    currentOrderNo: null,
    isVip: false,
    // i18n
    tBalanceScissorHairs: '剪刀发丝',
    tBalanceCombHairs: '梳子发丝',
    tBalanceTotal: '总计',
    tBalanceSelectAmount: '选择充值金额',
    tBalanceRecommended: '推荐',
    tBalancePayNow: '立即支付',
    tBalanceRechargeDesc: '充值说明：',
    tBalanceRechargeTip1: '充值后发丝立即到账',
    tBalanceRechargeTip2: '剪刀槽发丝优先消费',
    tBalanceRechargeTip3: '如有疑问请联系客服',
    tBalancePleaseSelectAmount: '请选择充值金额',
    tBalanceCreatingOrder: '创建订单中...',
    tBalanceDevModePaySuccess: '开发者模式：充值 {amount} 元成功，头发丝已到账',
    tBalanceSimulatedPay: '模拟支付',
    tBalanceGetPayParamsFail: '获取虚拟支付参数失败',
    tBalancePaySuccess: '支付成功',
    tBalancePayFail: '支付失败',
    tBalancePayCancel: '已取消支付',
    tBalancePayTimeout: '支付处理超时',
    tBalanceQueryFail: '查询订单失败',
    tBalanceProcessing: '处理中...',
    tBalanceCreateOrderFail: '创建订单失败',
    tBalanceVirtualPayFail: '调起支付失败',
    tBalanceVirtualPayTitle: '微信虚拟支付',
    tBalanceVirtualPayNotice: '本商品为虚拟商品，通过微信官方虚拟支付购买',
    tBalanceVipDiscount: '会员专享优惠',
    tBalanceVirtualPay: '虚拟支付',
    tBalanceVirtualPayHint: '通过微信官方虚拟支付完成购买',
    tBalanceHairsNormal10: '',
    tBalanceHairsNormal20: '',
    tBalanceHairsNormal50: '',
    tBalanceHairsNormal100: '',
    tBalanceHairsVip10: '',
    tBalanceHairsVip20: '',
    tBalanceHairsVip50: '',
    tBalanceHairsVip100: ''
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'balance.title')
    this.loadUserInfo()
  },

  onShow() {
    this._loadI18n()
    app.setNavTitle(this, 'balance.title')
    this.loadUserInfo()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'balance.title')
    })
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    const amount = this.data.selectedAmount || 0

    this.setData({
      tBalanceScissorHairs: t('profile.scissorHairs'),
      tBalanceCombHairs: t('profile.combHairs'),
      tBalanceTotal: t('index.total'),
      tBalanceSelectAmount: t('balance.selectAmount'),
      tBalanceRecommended: t('balance.recommended'),
      tBalancePayNow: t('balance.payNow'),
      tBalanceRechargeDesc: t('balance.rechargeDesc'),
      tBalanceRechargeTip1: t('balance.rechargeTip1'),
      tBalanceRechargeTip2: t('balance.rechargeTip2'),
      tBalanceRechargeTip3: t('balance.rechargeTip3'),
      tBalancePleaseSelectAmount: t('balance.pleaseSelectAmount'),
      tBalanceCreatingOrder: t('balance.creatingOrder'),
      tBalanceDevModePaySuccess: t('balance.devModePaySuccess').replace('{amount}', String(amount)),
      tBalanceSimulatedPay: t('balance.simulatedPay'),
      tBalanceGetPayParamsFail: t('balance.getPayParamsFail'),
      tBalancePaySuccess: t('balance.paySuccess'),
      tBalancePayFail: t('balance.payFail'),
      tBalancePayCancel: t('balance.payCancel'),
      tBalancePayTimeout: t('balance.payTimeout'),
      tBalanceQueryFail: t('balance.queryFail'),
      tBalanceProcessing: t('balance.processing'),
      tBalanceCreateOrderFail: t('balance.createOrderFail'),
      tBalanceVirtualPayFail: t('balance.virtualPayFail'),
      tBalanceVirtualPayTitle: t('balance.virtualPayTitle'),
      tBalanceVirtualPayNotice: t('balance.virtualPayNotice'),
      tBalanceVipDiscount: t('balance.vipDiscount'),
      tBalanceVirtualPay: t('balance.virtualPay'),
      tBalanceVirtualPayHint: t('balance.virtualPayHint'),
      tBalanceHairsNormal10: t('balance.hairsNormal10'),
      tBalanceHairsNormal20: t('balance.hairsNormal20'),
      tBalanceHairsNormal50: t('balance.hairsNormal50'),
      tBalanceHairsNormal100: t('balance.hairsNormal100'),
      tBalanceHairsVip10: t('balance.hairsVip10'),
      tBalanceHairsVip20: t('balance.hairsVip20'),
      tBalanceHairsVip50: t('balance.hairsVip50'),
      tBalanceHairsVip100: t('balance.hairsVip100')
    })
  },

  /**
   * 加载用户信息
   */
  async loadUserInfo() {
    try {
      const res = await getUserInfo()

      if (res.success) {
        const userInfo = res.user
        const totalHairs = (userInfo.scissor_hairs || 0) + (userInfo.comb_hairs || 0)

        this.setData({
          scissorHairs: userInfo.scissor_hairs || 0,
          combHairs: userInfo.comb_hairs || 0,
          totalHairs: totalHairs,
          isVip: userInfo.member_level === 'vip' && !userInfo.is_member_expired
        })
      }
    } catch (e) {
      console.error('加载用户信息失败:', e)
    }
  },

  /**
   * 选择充值金额
   */
  selectAmount(e) {
    const amount = parseInt(e.currentTarget.dataset.amount)
    this.setData({ selectedAmount: amount })
  },

  /**
   * 创建订单并支付
   */
  async createOrder() {
    const amount = this.data.selectedAmount

    if (!amount) {
      wx.showToast({
        title: this.data.tBalancePleaseSelectAmount,
        icon: 'none'
      })
      return
    }

    try {
      wx.showLoading({ title: this.data.tBalanceCreatingOrder })
      await this.handleVirtualPay(amount)
    } catch (e) {
      console.error('创建订单失败:', e)
      wx.hideLoading()
      wx.showToast({
        title: e.error || e.message || this.data.tBalanceCreateOrderFail,
        icon: 'none'
      })
    }
  },

  /**
   * 处理支付（iOS 虚拟支付 / Android 普通微信支付）
   */
  async handleVirtualPay(amount) {
    // iOS 使用虚拟支付，Android 使用普通微信支付
    if (isIOS()) {
      await this.handleIOSVirtualPay(amount)
    } else {
      await this.handleAndroidWechatPay(amount)
    }
  },

  /**
   * iOS 虚拟支付
   */
  async handleIOSVirtualPay(amount) {
    const goodsKey = getVirtualGoodsKey('recharge', amount)

    const sessionKey = await getSessionKey()
    const orderRes = await createVirtualPayOrder('recharge', amount, goodsKey, sessionKey)

    if (!orderRes.success) {
      throw new Error(orderRes.error || app.t('balance.createOrderFail'))
    }

    const orderNo = orderRes.order_no
    this.setData({ currentOrderNo: orderNo })

    if (orderRes.is_developer_mode) {
      wx.hideLoading()
      wx.showModal({
        title: this.data.tBalanceSimulatedPay,
        content: this.data.tBalanceDevModePaySuccess.replace('{amount}', String(amount)),
        showCancel: false,
        success: () => {
          this.loadUserInfo()
        }
      })
      return
    }

    const payParams = orderRes.virtual_pay_params
    if (!payParams) {
      throw new Error(this.data.tBalanceGetPayParamsFail)
    }

    wx.hideLoading()

    try {
      await requestVirtualPay(payParams)
      this.checkVirtualPayOrderStatus(orderNo)
    } catch (err) {
      console.error('调起虚拟支付失败:', err)
      wx.showToast({
        title: this.data.tBalanceVirtualPayFail,
        icon: 'none'
      })
    }
  },

  /**
   * Android 普通微信支付
   */
  async handleAndroidWechatPay(amount) {
    // 创建订单
    const orderRes = await createWechatPayOrder(amount, 'wxpay')

    if (!orderRes.success) {
      throw new Error(orderRes.error || app.t('balance.createOrderFail'))
    }

    const orderNo = orderRes.order_no
    this.setData({ currentOrderNo: orderNo })

    // 获取微信支付参数
    const payRes = await payRechargeOrder(orderNo, 'wxpay')
    if (!payRes.success) {
      throw new Error(payRes.error || this.data.tBalanceGetPayParamsFail)
    }

    const payParams = payRes.wxpay_params
    if (!payParams) {
      throw new Error(this.data.tBalanceGetPayParamsFail)
    }

    wx.hideLoading()

    try {
      await requestWechatPay(payParams)
      // 支付成功后刷新用户信息
      wx.showToast({
        title: this.data.tBalancePaySuccess,
        icon: 'success'
      })
      setTimeout(() => {
        this.loadUserInfo()
      }, 1500)
    } catch (err) {
      console.error('调起微信支付失败:', err)
      wx.showToast({
        title: this.data.tBalanceVirtualPayFail,
        icon: 'none'
      })
    }
  },

  /**
   * 查询虚拟支付订单状态
   */
  async checkVirtualPayOrderStatus(orderNo) {
    wx.showLoading({ title: this.data.tBalanceProcessing })

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

            wx.showToast({
              title: this.data.tBalancePaySuccess,
              icon: 'success'
            })

            setTimeout(() => {
              this.loadUserInfo()
            }, 1500)

          } else if (paymentStatus === 'failed' || paymentStatus === 'cancelled') {
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({
              title: paymentStatus === 'failed' ? this.data.tBalancePayFail : this.data.tBalancePayCancel,
              icon: 'none'
            })

          } else if (count >= maxCount) {
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({
              title: this.data.tBalancePayTimeout,
              icon: 'none'
            })
          }
        }

      } catch (e) {
        clearInterval(timer)
        wx.hideLoading()
        console.error('查询虚拟支付订单状态失败:', e)
        wx.showToast({
          title: this.data.tBalanceQueryFail,
          icon: 'none'
        })
      }
    }, 2000)

    setTimeout(() => {
      clearInterval(timer)
      wx.hideLoading()
    }, 30000)
  }
})
