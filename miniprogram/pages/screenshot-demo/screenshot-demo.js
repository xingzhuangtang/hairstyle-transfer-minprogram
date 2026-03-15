// pages/screenshot-demo/screenshot-demo.js
Page({
  /**
   * 页面的初始数据
   */
  data: {},

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    wx.showToast({
      title: '此页面用于支付宝审核截图',
      icon: 'none',
      duration: 2000
    })
  }
})
