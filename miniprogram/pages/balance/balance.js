// pages/balance/balance.js
import { getUserInfo } from '../../api/user.js'
import { createRechargeOrder as createRechargeApi, pay, getOrderStatus } from '../../api/payment.js'
import { createVirtualPayOrder, getVirtualPayOrderStatus } from '../../api/payment.js'
import { needsVirtualPay, getVirtualGoodsKey } from '../../utils/platform.js'
import { onLocaleChange } from '../../utils/i18n.js'

Page({
  data: {
    scissorHairs: 0,
    combHairs: 0,
    totalHairs: 0,
    selectedAmount: null,
    paymentMethod: 'wechat',
    currentOrderNo: null,
    isVirtualPay: false,
    isDevTools: false,
    isVip: false,
    // i18n
    tBalanceScissorHairs: '剪刀发丝',
    tBalanceCombHairs: '梳子发丝',
    tBalanceTotal: '总计',
    tBalanceSelectAmount: '选择充值金额',
    tBalanceSelectPayment: '选择支付方式',
    tBalanceWechatPay: '微信支付',
    tBalanceAlipay: '支付宝',
    tBalanceRecommended: '推荐',
    tBalancePayNow: '立即支付',
    tBalanceRechargeDesc: '充值说明：',
    tBalanceRechargeTip1: '充值后发丝立即到账',
    tBalanceRechargeTip2: '剪刀槽发丝优先消费',
    tBalanceRechargeTip3: '如有疑问请联系客服',
    tBalancePleaseSelectAmount: '请选择充值金额',
    tBalancePleaseSelectPayment: '请选择支付方式',
    tBalanceCreatingOrder: '创建订单中...',
    tBalanceDevModePaySuccess: '开发者模式：充值 {amount} 元成功，头发丝已到账',
    tBalanceVirtualPayTip: '正在调起微信虚拟支付 ¥{amount}',
    tBalancePaySuccess: '支付成功',
    tBalancePayFail: '支付失败',
    tBalancePayCancel: '取消支付',
    tBalancePayTimeout: '支付处理超时',
    tBalanceQueryFail: '查询订单失败',
    tBalanceProcessing: '处理中...',
    tBalanceComingSoon: '功能开发中',
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
    this.checkPlatform()
  },

  onShow() {
    this._loadI18n()
    app.setNavTitle(this, 'balance.title')
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'balance.title')
    })
  },

  _loadI18n() {
    const app = getApp()
    const t = (key) => app.t(key)
    const amount = this.data.selectedAmount || 0

    this.setData({
      tBalanceScissorHairs: t('profile.scissorHairs'),
      tBalanceCombHairs: t('profile.combHairs'),
      tBalanceTotal: t('index.total'),
      tBalanceSelectAmount: t('balance.selectAmount'),
      tBalanceSelectPayment: t('balance.selectPayment'),
      tBalanceWechatPay: t('balance.wechatPay'),
      tBalanceAlipay: t('balance.alipay'),
      tBalanceRecommended: t('balance.recommended'),
      tBalancePayNow: t('balance.payNow'),
      tBalanceRechargeDesc: t('balance.rechargeDesc'),
      tBalanceRechargeTip1: t('balance.rechargeTip1'),
      tBalanceRechargeTip2: t('balance.rechargeTip2'),
      tBalanceRechargeTip3: t('balance.rechargeTip3'),
      tBalancePleaseSelectAmount: t('balance.pleaseSelectAmount'),
      tBalancePleaseSelectPayment: t('balance.pleaseSelectPayment'),
      tBalanceCreatingOrder: t('balance.creatingOrder'),
      tBalanceDevModePaySuccess: t('balance.devModePaySuccess').replace('{amount}', String(amount)),
      tBalanceVirtualPayTip: t('balance.virtualPayTip').replace('{amount}', String(amount)),
      tBalancePaySuccess: t('balance.paySuccess'),
      tBalancePayFail: t('balance.payFail'),
      tBalancePayCancel: t('balance.payCancel'),
      tBalancePayTimeout: t('balance.payTimeout'),
      tBalanceQueryFail: t('balance.queryFail'),
      tBalanceProcessing: t('balance.processing'),
      tBalanceComingSoon: t('common.comingSoon'),
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

    console.log('充值页平台检测:', {
      platform: systemInfo.platform,
      isVirtualPay: isVirtual,
      isDevTools: isDev
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
    this.setData({
      selectedAmount: amount
    })
  },

  /**
   * 选择支付方式
   */
  selectPaymentMethod(e) {
    const method = e.currentTarget.dataset.method
    this.setData({
      paymentMethod: method
    })
  },

  /**
   * 处理支付宝不可用提示
   */
  handleAlipayNotAvailable() {
    wx.showToast({
      title: this.data.tBalanceComingSoon,
      icon: 'none'
    })
  },

  /**
   * 创建订单并支付
   */
  async createOrder() {
    const amount = this.data.selectedAmount
    const paymentMethod = this.data.paymentMethod

    if (!amount) {
      wx.showToast({
        title: this.data.tBalancePleaseSelectAmount,
        icon: 'none'
      })
      return
    }

    if (!paymentMethod) {
      wx.showToast({
        title: this.data.tBalancePleaseSelectPayment,
        icon: 'none'
      })
      return
    }

    try {
      wx.showLoading({ title: this.data.tBalanceCreatingOrder })

      // iOS端使用虚拟支付
      if (this.data.isVirtualPay || this.data.isDevTools) {
        await this.handleVirtualPay(amount)
      } else {
        // Android端使用普通微信支付
        await this.handleNormalPay(amount, paymentMethod)
      }

    } catch (e) {
      console.error('创建订单失败:', e)
      wx.hideLoading()
      wx.showToast({
        title: e.error || e.message || getApp().t('balance.createOrderFail'),
        icon: 'none'
      })
    }
  },

  /**
   * 处理普通微信支付（Android端）
   */
  async handleNormalPay(amount, paymentMethod) {
    // 1. 创建充值订单
    const orderRes = await createRechargeApi(amount, paymentMethod)

    if (!orderRes.success) {
      throw new Error(orderRes.error || getApp().t('balance.createOrderFail'))
    }

    const orderNo = orderRes.order_no
    this.setData({ currentOrderNo: orderNo })

    // 2. 调用微信支付
    await this.handleWechatPay(orderNo)
  },

  /**
   * 处理微信虚拟支付（iOS端）
   */
  async handleVirtualPay(amount) {
    const goodsKey = getVirtualGoodsKey('recharge', amount)

    // 1. 创建虚拟支付订单
    const orderRes = await createVirtualPayOrder('recharge', amount, goodsKey)

    if (!orderRes.success) {
      throw new Error(orderRes.error || getApp().t('balance.createVirtualOrderFail'))
    }

    const orderNo = orderRes.order_no
    this.setData({ currentOrderNo: orderNo })

    // 2. 开发者模式：直接显示成功
    if (orderRes.is_developer_mode) {
      wx.hideLoading()
      wx.showModal({
        title: getApp().t('balance.simulatedPay'),
        content: getApp().t('balance.devModePaySuccess', { amount: amount }),
        showCancel: false,
        success: () => {
          this.loadUserInfo()  // 刷新用户信息
        }
      })
      return
    }

    // 3. 正常模式：调起虚拟支付并轮询
    wx.hideLoading()
    wx.showModal({
      title: getApp().t('balance.virtualPay'),
      content: getApp().t('balance.virtualPayContent', { amount: amount }),
      showCancel: false,
      success: () => {
        this.checkVirtualPayOrderStatus(orderNo)
      }
    })
  },

  /**
   * 处理微信支付
   */
  async handleWechatPay(orderNo) {
    try {
      // 获取支付参数
      const payRes = await pay(orderNo, 'wechat')

      if (!payRes.success) {
        throw new Error(payRes.error || getApp().t('balance.getPayParamsFail'))
      }

      wx.hideLoading()

      // 调起微信支付
      wx.requestPayment({
        ...payRes.wxpay_params,
        total_fee: payRes.wxpay_params.total_fee || 0,
        success: () => {
          // 支付成功，查询订单状态
          this.checkOrderStatus(orderNo)
        },
        fail: (err) => {
          if (err.errMsg.includes('cancel')) {
            wx.showToast({
              title: this.data.tBalancePayCancel,
              icon: 'none'
            })
          } else {
            wx.showToast({
              title: this.data.tBalancePayFail,
              icon: 'none'
            })
          }
        }
      })
    } catch (e) {
      throw e
    }
  },

  /**
   * 查询虚拟支付订单状态（iOS端）
   */
  async checkVirtualPayOrderStatus(orderNo) {
    wx.showLoading({ title: this.data.tBalanceProcessing })

    // 轮询查询（最多 30 秒）
    let count = 0
    const maxCount = 15 // 最多查询 15 次 (15 * 2 秒 = 30 秒)
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

    // 30 秒后停止轮询
    setTimeout(() => {
      clearInterval(timer)
      wx.hideLoading()
    }, 30000)
  },

  /**
   * 查询订单状态
   */
  async checkOrderStatus(orderNo) {
    wx.showLoading({ title: this.data.tBalanceProcessing })

    // 轮询查询（最多 30 秒）
    let count = 0
    const maxCount = 15 // 最多查询 15 次 (15 * 2 秒 = 30 秒)
    const timer = setInterval(async () => {
      count++

      try {
        // 调用查询订单状态的 API
        const res = await getOrderStatus(orderNo)

        if (res.success) {
          const paymentStatus = res.payment_status

          if (paymentStatus === 'success') {
            // 支付成功
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
            // 支付失败或取消
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({
              title: paymentStatus === 'failed' ? this.data.tBalancePayFail : this.data.tBalancePayCancel,
              icon: 'none'
            })

          } else if (count >= maxCount) {
            // 超时
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({
              title: this.data.tBalancePayTimeout,
              icon: 'none'
            })
          }
          // 如果状态是 pending，继续轮询
        }

      } catch (e) {
        clearInterval(timer)
        wx.hideLoading()
        console.error('查询订单状态失败:', e)
        wx.showToast({
          title: this.data.tBalanceQueryFail,
          icon: 'none'
        })
      }
    }, 2000) // 每 2 秒查询一次

    // 30 秒后停止轮询
    setTimeout(() => {
      clearInterval(timer)
      wx.hideLoading()
    }, 30000)
  },

  /**
   * 页面显示时检查订单状态（从支付宝支付页面返回时调用）
   */
  onShow() {
    // 如果有当前订单号，检查支付状态
    if (this.data.currentOrderNo) {
      // 延迟检查，给支付回调一些时间
      setTimeout(() => {
        this.checkOrderStatus(this.data.currentOrderNo)
        // 清空当前订单号，避免重复检查
        this.setData({ currentOrderNo: null })
      }, 1000)
    }
  }
})
