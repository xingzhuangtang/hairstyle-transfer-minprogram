// pages/legal/legal.js
const { onLocaleChange } = require('../../utils/i18n.js')

const app = getApp()

Page({
  data: {
    title: '',
    version: '',
    updateDate: '',
    content: '',
    // i18n
    tLegalLoading: '',
    tLegalLoadFail: '',
    tLegalNetworkError: '',
    tDefaultTitle: '',
    tLegalVersionLabel: '',
    tLegalUpdateDateLabel: ''
  },

  onLoad(options) {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'legal.title')

    const type = options.type || 'agreement'
    const title = options.title || this.data.tDefaultTitle

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
      wx.showLoading({ title: this.data.tLegalLoading })
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
            wx.showToast({ title: this.data.tLegalLoadFail, icon: 'none' })
          }
        },
        fail: (err) => {
          wx.hideLoading()
          console.error('加载失败:', err)
          wx.showToast({ title: this.data.tLegalNetworkError, icon: 'none' })
        }
      })
    } else {
      this.setData({
        content: html,
        version: version,
        updateDate: updateDate
      })
    }
  },

  onShow() {
    this._loadI18n()
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tLegalLoading: t('legal.loading'),
      tLegalLoadFail: t('legal.loadFail'),
      tLegalNetworkError: t('legal.networkError'),
      tDefaultTitle: t('legal.defaultTitle'),
      tLegalVersionLabel: t('legal.versionLabel'),
      tLegalUpdateDateLabel: t('legal.updateDateLabel')
    })
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
    })
  }
})
