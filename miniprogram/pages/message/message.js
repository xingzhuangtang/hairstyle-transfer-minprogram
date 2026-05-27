// pages/message/message.js
import { API_BASE_URL } from '../../utils/constants.js'

Page({
  data: {
    name: '',
    phone: '',
    content: '',
    submitting: false
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
              reject(new Error(res.data.error || '提交失败'))
            }
          },
          fail: (err) => {
            reject(new Error('网络请求失败'))
          }
        })
      })

      // 提交成功
      wx.showToast({
        title: '留言提交成功',
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
        title: e.message || '提交失败，请重试',
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
        title: '请输入姓名',
        icon: 'none'
      })
      return false
    }

    if (name.length > 20) {
      wx.showToast({
        title: '姓名最多20个字符',
        icon: 'none'
      })
      return false
    }

    if (!phone || phone.length !== 11) {
      wx.showToast({
        title: '请输入11位手机号码',
        icon: 'none'
      })
      return false
    }

    if (!content || !content.trim()) {
      wx.showToast({
        title: '请输入留言内容',
        icon: 'none'
      })
      return false
    }

    if (content.length > 500) {
      wx.showToast({
        title: '留言内容最多500个字符',
        icon: 'none'
      })
      return false
    }

    return true
  }
})
