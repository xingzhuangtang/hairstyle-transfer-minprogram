// pages/balance/balance.js
import { getUserInfo } from '../../api/user.js'
import { createRechargeOrder as createRechargeApi, pay, getOrderStatus } from '../../api/payment.js'
import { createVirtualPayOrder, getVirtualPayOrderStatus } from '../../api/payment.js'
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
        title: e.error || e.message || '创建订单失败',
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
      throw new Error(orderRes.error || '创建订单失败')
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
      throw new Error(orderRes.error || '创建虚拟支付订单失败')
    }

    const orderNo = orderRes.order_no
    this.setData({ currentOrderNo: orderNo })

    // 2. 开发者模式：直接显示成功
    if (orderRes.is_developer_mode) {
      wx.hideLoading()
      wx.showModal({
        title: '模拟支付',
        content: `开发者模式：充值 ${amount} 元成功，头发丝已到账`,
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
      title: '虚拟支付',
      content: `正在调起微信虚拟支付 ¥${amount}`,
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
        throw new Error(payRes.error || '获取支付参数失败')
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
              title: '取消支付',
              icon: 'none'
            })
          } else {
            wx.showToast({
              title: '支付失败',
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

  /**
   * 查询订单状态
   */
  async checkOrderStatus(orderNo) {
    wx.showLoading({ title: '处理中...' })

    // 轮询查询（最多 30 秒）
    let count = 0
    const maxCount = 30 // 最多查询 30 次 (30 * 1 秒 = 30 秒)

    // 立即查询一次（不等 1 秒）
    const checkOnce = async () => {
      count++

      try {
        const res = await getOrderStatus(orderNo)

        if (res.success) {
          const paymentStatus = res.payment_status

          if (paymentStatus === 'success') {
            wx.hideLoading()
            wx.showToast({ title: '支付成功', icon: 'success' })
            setTimeout(() => this.loadUserInfo(), 1000)
            return true
          } else if (paymentStatus === 'failed' || paymentStatus === 'cancelled') {
            wx.hideLoading()
            wx.showToast({
              title: paymentStatus === 'failed' ? '支付失败' : '已取消支付',
              icon: 'none'
            })
            return true
          }
        }
        return false
      } catch (e) {
        console.error('查询订单状态失败:', e)
        return false
      }
    }

    // 立即查询第一次
    const done = await checkOnce()
    if (done) return

    // 之后每秒轮询
    const timer = setInterval(async () => {
      if (count >= maxCount) {
        clearInterval(timer)
        await this.queryWechatPayStatus(orderNo)
        return
      }

      const done = await checkOnce()
      if (done) clearInterval(timer)
    }, 1000) // 每 1 秒查询一次

    // 30 秒后停止轮询（兜底）
    setTimeout(() => clearInterval(timer), 30000)
  },

  /**
   * 主动查询微信支付状态（轮询超时后调用）
   */
  async queryWechatPayStatus(orderNo) {
    try {
      wx.showLoading({ title: '查询支付状态...' })

      const { get } = require('../../utils/request.js')
      const res = await get(`/api/recharge/query-wechat/${orderNo}`)

      wx.hideLoading()

      if (res.success) {
        if (res.payment_status === 'success') {
          wx.showToast({
            title: '支付成功',
            icon: 'success'
          })

          setTimeout(() => {
            this.loadUserInfo()
          }, 1500)
        } else if (res.payment_status === 'failed') {
          wx.showToast({
            title: '支付失败',
            icon: 'none'
          })
        } else {
          wx.showToast({
            title: '支付处理中，请稍后查看',
            icon: 'none'
          })
        }
      } else {
        wx.showToast({
          title: res.error || '查询失败',
          icon: 'none'
        })
      }
    } catch (e) {
      wx.hideLoading()
      console.error('主动查询微信支付状态失败:', e)
      wx.showToast({
        title: '查询失败，请稍后查看',
        icon: 'none'
      })
    }
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
