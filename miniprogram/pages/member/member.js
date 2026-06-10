// pages/member/member.js
import { getMemberInfo, buyMember, getMemberOrders, payMemberOrder } from '../../api/member.js'
import { getUserInfo } from '../../api/user.js'
import { createVirtualPayOrder, getVirtualPayOrderStatus } from '../../api/payment.js'
import { needsVirtualPay, getVirtualGoodsKey } from '../../utils/platform.js'

Page({
  data: {
    userInfo: {},
    isVip: false,
    remainingDays: 0,
    expireAt: '',
    orders: [],
    isVirtualPay: false, // 是否使用虚拟支付（iOS端）
    isDevTools: false
  },

  onLoad() {
    this.loadMemberInfo()
    this.checkPlatform()
  },

  onShow() {
    this.loadMemberInfo()
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
          created_at: this.formatDate(order.created_at)
        }))
        this.setData({ orders })
      }
    } catch (e) {
      console.error('加载会员订单失败:', e)
    }
  },

  async buyMember() {
    wx.showModal({
      title: '确认开通',
      content: '开通陪跑会员 ¥99/年，购买即赠 1000 发丝，确认继续？',
      success: async (modalRes) => {
        if (modalRes.confirm) {
          try {
            wx.showLoading({ title: '创建订单中...' })

            // iOS端使用虚拟支付
            if (this.data.isVirtualPay || this.data.isDevTools) {
              await this.handleVirtualPay()
            } else {
              // Android端使用普通微信支付
              await this.handleNormalPay()
            }
          } catch (e) {
            wx.hideLoading()
            wx.showToast({ title: e.message || '创建订单失败', icon: 'none' })
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
      title: '虚拟支付',
      content: '正在调起微信虚拟支付 ¥99',
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
          wx.showToast({ title: '支付成功', icon: 'success' })
          setTimeout(() => this.loadMemberInfo(), 1500)
        },
        fail: (err) => {
          wx.showToast({
            title: err.errMsg.includes('cancel') ? '取消支付' : '支付失败',
            icon: 'none'
          })
        }
      })
    } catch (e) {
      wx.showToast({ title: e.message || '发起支付失败', icon: 'none' })
    }
  },

  /**
   * 查询虚拟支付订单状态（iOS端）
   */
  async checkVirtualPayOrderStatus(orderNo) {
    wx.showLoading({ title: '处理中...' })

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

            wx.showToast({ title: '支付成功，会员已开通', icon: 'success' })
            setTimeout(() => this.loadMemberInfo(), 1500)

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
            wx.showToast({ title: '支付处理超时', icon: 'none' })
          }
        }

      } catch (e) {
        clearInterval(timer)
        wx.hideLoading()
        console.error('查询虚拟支付订单状态失败:', e)
        wx.showToast({ title: '查询订单失败', icon: 'none' })
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
    const map = { 'success': '已支付', 'pending': '待支付', 'failed': '支付失败' }
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
      countdownText = '已过期'
    } else {
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
      const diffDays = Math.floor(diffHours / 24)

      if (diffDays >= 1) {
        countdownText = `剩余${diffDays}天`
      } else {
        countdownText = `剩余${diffHours}小时`
      }
    }

    this.setData({ expireCountdownText: countdownText })
  },

  startCountdownTimer() {
    this.stopCountdownTimer()
    this.updateCountdown()
    this.data.countdownTimer = setInterval(() => {
      this.updateCountdown()
    }, 60 * 60 * 1000) // 每小时更新一次
  },

  stopCountdownTimer() {
    if (this.data.countdownTimer) {
      clearInterval(this.data.countdownTimer)
      this.setData({ countdownTimer: null })
    }
  }
})
