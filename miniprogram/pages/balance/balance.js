// pages/balance/balance.js
import { getUserInfo } from '../../api/user.js'
import { createRechargeOrder as createRechargeApi, pay, getOrderStatus } from '../../api/payment.js'

Page({
  data: {
    scissorHairs: 0,
    combHairs: 0,
    totalHairs: 0,
    selectedAmount: null,
    paymentMethod: 'wechat', // 默认微信支付
    currentOrderNo: null // 当前订单号
  },

  onLoad() {
    this.loadUserInfo()
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
          totalHairs: totalHairs
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

      // 1. 创建充值订单
      const orderRes = await createRechargeApi(amount, paymentMethod)

      if (!orderRes.success) {
        throw new Error(orderRes.error || '创建订单失败')
      }

      const orderNo = orderRes.order_no
      this.setData({ currentOrderNo: orderNo })

      // 2. 根据支付方式处理
      if (paymentMethod === 'wechat') {
        // 微信支付
        await this.handleWechatPay(orderNo)
      } else if (paymentMethod === 'alipay') {
        // 支付宝支付
        await this.handleAlipayPay(orderNo)
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

      // 检查是否是模拟支付
      if (payRes.mock) {
        wx.showModal({
          title: '模拟支付',
          content: '开发环境模拟支付成功，充值已到账',
          showCancel: false,
          success: () => {
            this.checkOrderStatus(orderNo)
          }
        })
        return
      }

      // 调起微信支付
      await wx.requestPayment({
        ...payRes.wxpay_params,
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
   * 处理支付宝支付
   */
  async handleAlipayPay(orderNo) {
    try {
      // 获取支付参数（H5支付URL）
      const payRes = await pay(orderNo, 'alipay')

      if (!payRes.success) {
        throw new Error(payRes.error || '获取支付参数失败')
      }

      wx.hideLoading()

      // 跳转到支付宝H5支付页面（使用web-view）
      const h5PayUrl = payRes.h5_pay_url

      wx.navigateTo({
        url: `/pages/alipay-web/alipay-web?h5_pay_url=${encodeURIComponent(h5PayUrl)}`
      })

    } catch (e) {
      throw e
    }
  },

  /**
   * 查询订单状态
   */
  async checkOrderStatus(orderNo) {
    wx.showLoading({ title: '处理中...' })

    // 轮询查询（最多30秒）
    let count = 0
    const maxCount = 15 // 最多查询15次 (15 * 2秒 = 30秒)
    const timer = setInterval(async () => {
      count++

      try {
        // 调用查询订单状态的API
        const res = await getOrderStatus(orderNo)

        if (res.success) {
          const paymentStatus = res.payment_status

          if (paymentStatus === 'success') {
            // 支付成功
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
            // 支付失败或取消
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({
              title: paymentStatus === 'failed' ? '支付失败' : '已取消支付',
              icon: 'none'
            })

          } else if (count >= maxCount) {
            // 超时
            clearInterval(timer)
            wx.hideLoading()

            wx.showToast({
              title: '支付处理超时',
              icon: 'none'
            })
          }
          // 如果状态是pending，继续轮询
        }

      } catch (e) {
        clearInterval(timer)
        wx.hideLoading()
        console.error('查询订单状态失败:', e)
        wx.showToast({
          title: '查询订单失败',
          icon: 'none'
        })
      }
    }, 2000) // 每2秒查询一次

    // 30秒后停止轮询
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
