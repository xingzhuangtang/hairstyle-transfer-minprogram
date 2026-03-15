// pages/alipay-web/alipay-web.js
Page({
  /**
   * 页面的初始数据
   */
  data: {
    h5PayUrl: ''
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    const { h5_pay_url } = options

    if (!h5_pay_url) {
      wx.showToast({
        title: '支付链接无效',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 2000)
      return
    }

    // 解码URL（微信小程序传递时可能被编码）
    const h5PayUrl = decodeURIComponent(h5_pay_url)

    this.setData({
      h5PayUrl: h5PayUrl
    })

    console.log('支付宝H5支付页面加载:', h5PayUrl)
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {
  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {
    // 页面卸载时，检查支付状态
    // 可以通过页面参数或全局数据获取订单号
    const pages = getCurrentPages()
    const prevPage = pages[pages.length - 2]

    if (prevPage && prevPage.checkOrderStatus) {
      // 如果上一个页面有检查订单状态的方法，延迟调用
      setTimeout(() => {
        prevPage.checkOrderStatus()
      }, 1000)
    }
  },

  /**
   * web-view消息回调
   */
  handleMessage(e) {
    console.log('收到web-view消息:', e.detail.data)
    const message = e.detail.data[0]

    if (message && message.type) {
      switch (message.type) {
        case 'payment_success':
          this.handlePaymentSuccess(message.data)
          break
        case 'payment_failed':
          this.handlePaymentFailed(message.data)
          break
        case 'payment_cancelled':
          this.handlePaymentCancelled()
          break
      }
    }
  },

  /**
   * 处理支付成功
   */
  handlePaymentSuccess(data) {
    wx.showToast({
      title: '支付成功',
      icon: 'success'
    })

    // 延迟返回，让用户看到成功提示
    setTimeout(() => {
      wx.navigateBack()
    }, 1500)
  },

  /**
   * 处理支付失败
   */
  handlePaymentFailed(data) {
    wx.showToast({
      title: data.message || '支付失败',
      icon: 'none'
    })
  },

  /**
   * 处理支付取消
   */
  handlePaymentCancelled() {
    wx.showToast({
      title: '取消支付',
      icon: 'none'
    })
  }
})
