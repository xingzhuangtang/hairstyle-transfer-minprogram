// pages/member/member.js
import { getMemberInfo, buyMember, getMemberOrders, payMemberOrder } from '../../api/member.js'
import { getUserInfo } from '../../api/user.js'

Page({
  data: {
    userInfo: {},
    isVip: false,
    remainingDays: 0,
    expireAt: '',
    orders: []
  },

  onLoad() {
    this.loadMemberInfo()
  },

  onShow() {
    this.loadMemberInfo()
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
            const orderRes = await buyMember('wechat')
            if (!orderRes.success) throw new Error(orderRes.error)

            const orderNo = orderRes.order_no
            this.setData({ currentOrderNo: orderNo })
            wx.hideLoading()
            this.handleWechatPay(orderNo)
          } catch (e) {
            wx.hideLoading()
            wx.showToast({ title: e.message || '创建订单失败', icon: 'none' })
          }
        }
      }
    })
  },

  async handleWechatPay(orderNo) {
    try {
      const payRes = await payMemberOrder(orderNo, 'wechat')
      if (!payRes.success) throw new Error(payRes.error)

      // 检查是否是 mock 支付
      if (payRes.mock) {
        wx.showModal({
          title: '模拟支付',
          content: '开发环境模拟支付成功，会员已开通',
          showCancel: false,
          success: () => {
            this.loadMemberInfo()
          }
        })
        return
      }

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
  }
})
