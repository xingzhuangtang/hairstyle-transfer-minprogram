// pages/login/login.js
import { wechatLogin, phoneLogin as phoneLoginApi, sendVerificationCode, redirectAfterLogin } from '../../utils/auth.js'
import { API_BASE_URL } from '../../utils/constants.js'

Page({
  data: {
    phone: '',
    code: '',
    agreed: false,
    wechatLoading: false,
    phoneLoading: false,
    counting: false,
    countDown: 60,
    timer: null
  },

  onLoad() {
    console.log('登录页面加载')
  },

  onUnload() {
    // 清除定时器
    if (this.data.timer) {
      clearInterval(this.data.timer)
    }
  },

  /**
   * 手机号输入
   */
  onPhoneInput(e) {
    this.setData({
      phone: e.detail.value
    })
  },

  /**
   * 验证码输入
   */
  onCodeInput(e) {
    this.setData({
      code: e.detail.value
    })
  },

  /**
   * 协议勾选
   */
  onAgreementChange(e) {
    this.setData({
      agreed: e.detail.value.includes('agree')
    })
  },

  /**
   * 微信登录
   */
  async onWechatLogin(e) {
    // 检查是否同意协议
    if (!this.data.agreed) {
      wx.showToast({
        title: '请先同意用户协议和隐私政策',
        icon: 'none'
      })
      return
    }

    // 获取用户信息
    const { userInfo } = e.detail

    if (!userInfo) {
      wx.showToast({
        title: '需要授权才能登录',
        icon: 'none'
      })
      return
    }

    this.setData({ wechatLoading: true })

    try {
      // 调用微信登录
      const res = await wechatLogin()

      if (res.success) {
        wx.showToast({
          title: '登录成功',
          icon: 'success'
        })

        // 延迟跳转
        setTimeout(() => {
          redirectAfterLogin()
        }, 1500)
      } else {
        wx.showToast({
          title: res.error || '登录失败',
          icon: 'none'
        })
      }
    } catch (e) {
      console.error('微信登录失败:', e)
      wx.showToast({
        title: e.error || '登录失败',
        icon: 'none'
      })
    } finally {
      this.setData({ wechatLoading: false })
    }
  },

  /**
   * 发送验证码
   */
  async sendCode() {
    console.log('sendCode 被调用')
    console.log('手机号:', this.data.phone)
    console.log('是否同意协议:', this.data.agreed)

    // 验证手机号
    if (!this.validatePhone()) {
      return
    }

    // 检查是否同意协议
    if (!this.data.agreed) {
      wx.showToast({
        title: '请先同意用户协议和隐私政策',
        icon: 'none'
      })
      return
    }

    try {
      console.log('开始发送验证码请求...')
      const res = await sendVerificationCode(this.data.phone)
      console.log('验证码请求返回:', res)

      if (res.success) {
        // 测试模式下显示验证码
        if (res.test_mode) {
          wx.showModal({
            title: '测试模式验证码',
            content: '验证码：' + res.code + '\n有效期：5 分钟',
            showCancel: false
          })
        } else {
          wx.showToast({
            title: '验证码已发送',
            icon: 'success'
          })
        }

        // 开始倒计时
        this.startCountDown()
      } else {
        wx.showToast({
          title: res.error || '发送失败',
          icon: 'none'
        })
      }
    } catch (e) {
      console.error('发送验证码失败:', e)
      wx.showToast({
        title: e.error || '发送失败',
        icon: 'none'
      })
    }
  },

  /**
   * 手机号登录
   */
  async onPhoneLogin() {
    // 验证手机号
    if (!this.validatePhone()) {
      return
    }

    // 验证验证码
    if (!this.data.code) {
      wx.showToast({
        title: '请输入验证码',
        icon: 'none'
      })
      return
    }

    // 检查是否同意协议
    if (!this.data.agreed) {
      wx.showToast({
        title: '请先同意用户协议和隐私政策',
        icon: 'none'
      })
      return
    }

    this.setData({ phoneLoading: true })

    try {
      const res = await phoneLoginApi(this.data.phone, this.data.code)

      if (res.success) {
        wx.showToast({
          title: '登录成功',
          icon: 'success'
        })

        // 延迟跳转
        setTimeout(() => {
          redirectAfterLogin()
        }, 1500)
      } else {
        wx.showToast({
          title: res.error || '登录失败',
          icon: 'none'
        })
      }
    } catch (e) {
      console.error('手机号登录失败:', e)
      wx.showToast({
        title: e.error || '登录失败',
        icon: 'none'
      })
    } finally {
      this.setData({ phoneLoading: false })
    }
  },

  /**
   * 验证手机号
   */
  validatePhone() {
    const phone = this.data.phone

    if (!phone) {
      wx.showToast({
        title: '请输入手机号',
        icon: 'none'
      })
      return false
    }

    // 验证手机号格式
    const phoneReg = /^1[3-9]\d{9}$/
    if (!phoneReg.test(phone)) {
      wx.showToast({
        title: '手机号格式不正确',
        icon: 'none'
      })
      return false
    }

    return true
  },

  /**
   * 开始倒计时
   */
  startCountDown() {
    this.setData({
      counting: true,
      countDown: 60
    })

    const timer = setInterval(() => {
      const countDown = this.data.countDown - 1

      if (countDown <= 0) {
        clearInterval(timer)
        this.setData({
          counting: false,
          countDown: 60,
          timer: null
        })
      } else {
        this.setData({
          countDown: countDown
        })
      }
    }, 1000)

    this.setData({
      timer: timer
    })
  },

  /**
   * 查看用户协议
   */
  viewUserAgreement() {
    wx.showLoading({ title: '加载中...' })
    
    // 调用后端 API 获取用户协议内容
    wx.request({
      url: 'https://xn--gmq63iba0780e.com/api/legal/user-agreement',
      method: 'GET',
      success: (res) => {
        wx.hideLoading()
        if (res.data.success || res.data.title) {
          // 使用富文本方式显示协议内容
          wx.setStorageSync('agreement_html', res.data.content)
          wx.navigateTo({
            url: '/pages/legal/legal?type=agreement&title=' + encodeURIComponent(res.data.title || '用户协议')
          })
        } else {
          wx.showToast({
            title: '加载失败',
            icon: 'none'
          })
        }
      },
      fail: (err) => {
        wx.hideLoading()
        console.error('获取用户协议失败:', err)
        wx.showToast({
          title: '网络错误，请稍后重试',
          icon: 'none'
        })
      }
    })
  },

  /**
   * 查看隐私政策
   */
  viewPrivacyPolicy() {
    wx.showLoading({ title: '加载中...' })
    
    // 调用后端 API 获取隐私政策内容
    wx.request({
      url: 'https://xn--gmq63iba0780e.com/api/legal/privacy-policy',
      method: 'GET',
      success: (res) => {
        wx.hideLoading()
        if (res.data.success || res.data.title) {
          // 使用富文本方式显示协议内容
          wx.setStorageSync('privacy_html', res.data.content)
          wx.navigateTo({
            url: '/pages/legal/legal?type=privacy&title=' + encodeURIComponent(res.data.title || '隐私政策')
          })
        } else {
          wx.showToast({
            title: '加载失败',
            icon: 'none'
          })
        }
      },
      fail: (err) => {
        wx.hideLoading()
        console.error('获取隐私政策失败:', err)
        wx.showToast({
          title: '网络错误，请稍后重试',
          icon: 'none'
        })
      }
    })
  }
})
