// pages/message/message.js
import { API_BASE_URL } from '../../utils/constants.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    name: '',
    phone: '',
    content: '',
    submitting: false,
    // i18n
    tMsgTitle: '',
    tMsgSubtitle: '',
    tMsgName: '',
    tMsgPhone: '',
    tMsgContent: '',
    tMsgNamePlaceholder: '',
    tMsgPhonePlaceholder: '',
    tMsgContentPlaceholder: '',
    tMsgSubmit: '',
    tMsgSubmitSuccess: '',
    tMsgSubmitFail: '',
    tMsgRequired: '',
    tMsgNameRequired: '',
    tMsgNameTooLong: '',
    tMsgPhoneRequired: '',
    tMsgContentRequired: '',
    tMsgContentTooLong: '',
    tMsgNetworkFail: ''
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
  },

  onShow() {
    this._loadI18n()
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tMsgTitle: t('message.title'),
      tMsgSubtitle: t('message.subtitle'),
      tMsgName: t('message.name'),
      tMsgPhone: t('message.phone'),
      tMsgContent: t('message.content'),
      tMsgNamePlaceholder: t('message.namePlaceholder'),
      tMsgPhonePlaceholder: t('message.phonePlaceholder'),
      tMsgContentPlaceholder: t('message.contentPlaceholder'),
      tMsgSubmit: t('message.submit'),
      tMsgSubmitSuccess: t('message.submitSuccess'),
      tMsgSubmitFail: t('message.submitFail'),
      tMsgRequired: t('message.required'),
      tMsgNameRequired: t('message.nameRequired'),
      tMsgNameTooLong: t('message.nameTooLong'),
      tMsgPhoneRequired: t('message.phoneRequired'),
      tMsgContentRequired: t('message.contentRequired'),
      tMsgContentTooLong: t('message.contentTooLong'),
      tMsgNetworkFail: t('message.networkFail')
    })
    this._updateNavTitle()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
    })
  },

  _updateNavTitle() {
    app.setNavTitle(this, 'message.title')
  },

  /**
   * 姓名输入
   */
  onNameInput(e) {
    this.setData({
      name: e.detail.value
    })
  },

  /**
   * 电话输入
   */
  onPhoneInput(e) {
    // 只允许数字
    const value = e.detail.value.replace(/[^\d]/g, '')
    this.setData({
      phone: value
    })
  },

  /**
   * 内容输入
   */
  onContentInput(e) {
    this.setData({
      content: e.detail.value
    })
  },

  /**
   * 提交留言
   */
  async onSubmit() {
    // 验证表单
    if (!this.validateForm()) {
      return
    }

    this.setData({ submitting: true })

    try {
      const { name, phone, content } = this.data

      await new Promise((resolve, reject) => {
        wx.request({
          url: `${API_BASE_URL}/api/messages`,
          method: 'POST',
          data: {
            name,
            phone,
            content
          },
          header: {
            'Content-Type': 'application/json'
          },
          success: (res) => {
            if (res.statusCode === 200) {
              resolve(res.data)
            } else {
              reject(new Error(res.data.error || this.data.tMsgSubmitFail))
            }
          },
          fail: (err) => {
            reject(new Error(this.data.tMsgNetworkFail))
          }
        })
      })

      // 提交成功
      wx.showToast({
        title: this.data.tMsgSubmitSuccess,
        icon: 'success',
        duration: 2000
      })

      // 清空表单
      this.setData({
        name: '',
        phone: '',
        content: ''
      })

      // 延迟返回上一页
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)

    } catch (e) {
      console.error('提交留言失败:', e)
      wx.showToast({
        title: e.message || this.data.tMsgSubmitFail,
        icon: 'none',
        duration: 2000
      })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /**
   * 验证表单
   */
  validateForm() {
    const { name, phone, content } = this.data

    if (!name || !name.trim()) {
      wx.showToast({
        title: this.data.tMsgNameRequired,
        icon: 'none'
      })
      return false
    }

    if (name.length > 20) {
      wx.showToast({
        title: this.data.tMsgNameTooLong,
        icon: 'none'
      })
      return false
    }

    if (!phone || phone.length !== 11) {
      wx.showToast({
        title: this.data.tMsgPhoneRequired,
        icon: 'none'
      })
      return false
    }

    if (!content || !content.trim()) {
      wx.showToast({
        title: this.data.tMsgContentRequired,
        icon: 'none'
      })
      return false
    }

    if (content.length > 500) {
      wx.showToast({
        title: this.data.tMsgContentTooLong,
        icon: 'none'
      })
      return false
    }

    return true
  }
})
