// pages/legal/legal.js
Page({
  data: {
    title: '',
    version: '',
    updateDate: '',
    content: ''
  },

  onLoad(options) {
    const type = options.type || 'agreement'
    const title = options.title || '协议内容'

    this.setData({ title })

    // 从缓存获取 HTML 内容
    let html = ''
    let version = '1.0.0'
    let updateDate = '2026-04-01'

    if (type === 'agreement') {
      html = wx.getStorageSync('agreement_html') || ''
    } else if (type === 'privacy') {
      html = wx.getStorageSync('privacy_html') || ''
    }

    // 如果没有缓存，重新请求 API
    if (!html) {
      wx.showLoading({ title: '加载中...' })
      const url = type === 'agreement'
        ? 'https://xn--gmq63iba0780e.com/api/legal/user-agreement'
        : 'https://xn--gmq63iba0780e.com/api/legal/privacy-policy'

      wx.request({
        url: url,
        method: 'GET',
        success: (res) => {
          wx.hideLoading()
          if (res.data.success || res.data.title) {
            this.setData({
              content: res.data.content,
              version: res.data.version || '1.0.0',
              updateDate: res.data.update_date || ''
            })
          } else {
            wx.showToast({ title: '加载失败', icon: 'none' })
          }
        },
        fail: (err) => {
          wx.hideLoading()
          console.error('加载失败:', err)
          wx.showToast({ title: '网络错误', icon: 'none' })
        }
      })
    } else {
      this.setData({
        content: html,
        version: version,
        updateDate: updateDate
      })
    }
  }
})
