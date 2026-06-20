// pages/balance/balance.js
import { getUserInfo } from '../../api/user.js'
import { createVirtualPayOrder, getVirtualPayOrderStatus, requestVirtualPay, getSessionKey } from '../../api/payment.js'
import { needsVirtualPay, getVirtualGoodsKey } from '../../utils/platform.js'

Page({
  data: {
    scissorHairs: 0,
    combHairs: 0,
    totalHairs: 0,
    selectedAmount: null,
    paymentMethod: 'wechat', // 默认微信支付
    currentOrderNo: null, // 当前订单号
    isVirtualPay: false, // 是否使用虚拟支付（iOS端）
    isDevTools: false, // 是否在开发者工具
    isVip: false // 是否VIP会员
  },

  onLoad() {
    this.loadUserInfo()
    this.checkPlatform()
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
      title: '功能开发中',
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
        title: '请选择充值金额',
        icon: 'none'
      })
      return
    }

    if (!paymentMethod) {
      wx.showToast({
        title: '请选择支付方式',
        icon: 'none'
      })
      return
    }

    try {
      wx.showLoading({ title: '创建订单中...' })
      await this.handleVirtualPay(amount)
    } catch (e) {
      console.error('创建订单失败:', e)
      wx.hideLoading()
      wx.showToast({
        title: e.error || e.message || '创建订单失败',
        icon: 'none'
      })
    }
  },

  /**
   * 处理微信虚拟支付
   */
  async handleVirtualPay(amount) {
    const goodsKey = getVirtualGoodsKey('recharge', amount)

    // 先获取 session_key（用于虚拟支付签名）
    const sessionKey = await getSessionKey()

    const orderRes = await createVirtualPayOrder('recharge', amount, goodsKey, sessionKey)

    if (!orderRes.success) {
      throw new Error(orderRes.error || '创建虚拟支付订单失败')
    }

    const orderNo = orderRes.order_no
    this.setData({ currentOrderNo: orderNo })

    if (orderRes.is_developer_mode) {
      wx.hideLoading()
      wx.showModal({
        title: '模拟支付',
        content: `开发者模式：充值 ${amount} 元成功，头发丝已到账`,
        showCancel: false,
        success: () => {
          this.loadUserInfo()
        }
      })
      return
    }

    const payParams = orderRes.virtual_pay_params
    if (!payParams) {
      throw new Error('获取虚拟支付参数失败')
    }

    wx.hideLoading()

    try {
      await requestVirtualPay(payParams)
      this.checkVirtualPayOrderStatus(orderNo)
    } catch (err) {
      console.error('调起虚拟支付失败:', err)
      wx.showToast({
        title: '调起支付失败',
        icon: 'none'
      })
    }
  },

  /**
   * 查询虚拟支付订单状态
   */
  async checkVirtualPayOrderStatus(orderNo) {
    wx.showLoading({ title: '处理中...' })

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
              title: '支付成功',
              icon: 'success'
            })

            setTimeout(() => {
              this.loadUserInfo()
            }, 1500)

          } else if (paymentStatus === 'failed' || paymentStatus === 'cancelled') {
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({
              title: paymentStatus === 'failed' ? '支付失败' : '已取消支付',
              icon: 'none'
            })

          } else if (count >= maxCount) {
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({
              title: '支付处理超时',
              icon: 'none'
            })
          }
        }

      } catch (e) {
        clearInterval(timer)
        wx.hideLoading()
        console.error('查询虚拟支付订单状态失败:', e)
        wx.showToast({
          title: '查询订单失败',
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

  onShow() {
    this.loadUserInfo()
  }
})
