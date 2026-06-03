// pages/login/login.js
import { wechatLogin, phoneLogin as phoneLoginApi, sendVerificationCode, redirectAfterLogin } from '../../utils/auth.js'
import { post, get } from '../../utils/request.js'
import { API_BASE_URL } from '../../utils/constants.js'
import { getDeviceInfo } from '../../utils/device.js'
import { setToken, setUserInfo } from '../../utils/storage.js'

Page({
  data: {
    phone: '',
    code: '',
    agreed: false,
    wechatLoading: false,
    phoneLoading: false,
    counting: false,
    countDown: 60,
    timer: null,
    nickName: '',
    // 手机号绑定相关
    showBindPhoneModal: false,
    bindPhone: '',
    bindCode: '',
    bindCounting: false,
    bindCountDown: 60,
    bindTimer: null,
    bindLoading: false,
    // 微信登录成功后暂存的 token 和用户信息
    pendingToken: '',
    pendingUserInfo: null
  },

  onLoad() {
    console.log('登录页面加载')
  },

  onUnload() {
    // 清除定时器
    if (this.data.timer) {
      clearInterval(this.data.timer)
    }
    if (this.data.bindTimer) {
      clearInterval(this.data.bindTimer)
    }
  },

  /**
   * 昵称输入回调
   */
  onNickNameInput(e) {
    this.setData({ nickName: e.detail.value })
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
  async onWechatLogin() {
    // 检查是否同意协议
    if (!this.data.agreed) {
      wx.showToast({
        title: '请先同意用户协议和隐私政策',
        icon: 'none'
      })
      return
    }

    this.setData({ wechatLoading: true })

    try {
      // 1. 获取 wx.login code
      const loginRes = await wx.login()
      if (!loginRes.code) {
        throw new Error('获取微信code失败')
      }

      // 2. 获取设备信息（使用共享模块）
      const deviceInfo = getDeviceInfo()

      // 3. 调用后端微信登录 API
      const res = await post('/api/auth/wechat/login', {
        code: loginRes.code,
        device_info: deviceInfo,
        nickname: this.data.nickName || '微信用户'
      })

      if (res.success) {
        // 保存 token 和用户信息
        setToken(res.token)
        setUserInfo(res.user)

        // 更新全局数据
        const app = getApp()
        app.globalData.token = res.token
        app.globalData.userInfo = res.user
        app.globalData.isPremium = res.user.member_level === 'vip'

        wx.showToast({
          title: '登录成功',
          icon: 'success'
        })

        // 检查是否需要绑定手机号
        if (res.needs_phone_bind) {
          // 暂存 token 和用户信息，等待绑定
          this.setData({
            pendingToken: res.token,
            pendingUserInfo: res.user,
            showBindPhoneModal: true
          })
        } else {
          // 已绑定手机号，直接跳转
          setTimeout(() => {
            redirectAfterLogin()
          }, 1500)
        }
      } else {
        wx.showToast({
          title: res.error || '登录失败',
          icon: 'none'
        })
      }
    } catch (e) {
      console.error('微信登录失败:', e)
      const errMsg = (typeof e === 'object') ? (e.error || e.message || '登录失败') : e
      wx.showToast({
        title: errMsg,
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
        wx.showToast({
          title: '验证码已发送',
          icon: 'success'
        })

        // 开始倒计时
        this.startCountDown()
      } else {
        wx.showToast({
          title: (typeof res.error === 'string' ? res.error : '发送失败'),
          icon: 'none'
        })
      }
    } catch (e) {
      console.error('发送验证码失败:', e)
      const errMsg = typeof e === 'object' ? (e.error || e.message || '发送失败') : e
      wx.showToast({
        title: errMsg,
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
      // 生成设备信息（使用共享模块）
      const deviceInfo = getDeviceInfo()

      const res = await phoneLoginApi(this.data.phone, this.data.code, deviceInfo)

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
        const errorMsg = res.error || '登录失败'
        if (errorMsg.includes('未注册')) {
          wx.showModal({
            title: '请先注册微信账号',
            content: '该手机号尚未注册。请先点击"微信一键登录"完成注册并绑定微信，之后即可使用手机号登录。',
            showCancel: false,
            confirmText: '去微信登录'
          })
        } else {
          wx.showToast({
            title: errorMsg,
            icon: 'none'
          })
        }
      }
    } catch (e) {
      console.error('手机号登录失败:', e)
      const errMsg = (typeof e === 'object') ? (e.error || e.message || '登录失败') : e
      wx.showToast({
        title: errMsg,
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
  },

  /**
   * 绑定手机号输入
   */
  onBindPhoneInput(e) {
    this.setData({ bindPhone: e.detail.value })
  },

  /**
   * 绑定验证码输入
   */
  onBindCodeInput(e) {
    this.setData({ bindCode: e.detail.value })
  },

  /**
   * 发送绑定验证码
   */
  async sendBindCode() {
    const phone = this.data.bindPhone
    if (!phone) {
      wx.showToast({ title: '请输入手机号', icon: 'none' })
      return
    }
    const phoneReg = /^1[3-9]\d{9}$/
    if (!phoneReg.test(phone)) {
      wx.showToast({ title: '手机号格式不正确', icon: 'none' })
      return
    }

    try {
      const res = await sendVerificationCode(phone)
      if (res.success) {
        wx.showToast({ title: '验证码已发送', icon: 'success' })
        this.startBindCountDown()
      } else {
        wx.showToast({ title: res.error || '发送失败', icon: 'none' })
      }
    } catch (e) {
      wx.showToast({ title: '发送失败', icon: 'none' })
    }
  },

  /**
   * 确认绑定手机号
   */
  async confirmBindPhone() {
    const phone = this.data.bindPhone
    const code = this.data.bindCode

    if (!phone) {
      wx.showToast({ title: '请输入手机号', icon: 'none' })
      return
    }
    if (!code) {
      wx.showToast({ title: '请输入验证码', icon: 'none' })
      return
    }

    this.setData({ bindLoading: true })

    try {
      const res = await post('/api/auth/bind-phone', {
        phone: phone,
        code: code
      })

      if (res.success) {
        wx.showToast({ title: '绑定成功', icon: 'success' })
        
        // 更新 token 和用户信息（可能合并到了已有账号）
        setToken(res.token)
        setUserInfo(res.user)

        const app = getApp()
        app.globalData.token = res.token
        app.globalData.userInfo = res.user
        app.globalData.isPremium = res.user.member_level === 'vip'

        this.setData({
          showBindPhoneModal: false,
          pendingToken: '',
          pendingUserInfo: null
        })

        setTimeout(() => {
          redirectAfterLogin()
        }, 1500)
      } else {
        // 如果是手机号已被其他用户绑定，询问是否合并
        if (res.error && res.error.includes('已被绑定')) {
          wx.showModal({
            title: '账号合并提示',
            content: '该手机号已绑定其他账号，是否合并到该账号？',
            confirmText: '合并',
            cancelText: '取消',
            success: async (modalRes) => {
              if (modalRes.confirm) {
                // 调用合并接口
                const mergeRes = await post('/api/auth/merge-account', {
                  phone: phone,
                  code: code
                })
                if (mergeRes.success) {
                  wx.showToast({ title: '合并成功', icon: 'success' })
                  setToken(mergeRes.token)
                  setUserInfo(mergeRes.user)
                  const app = getApp()
                  app.globalData.token = mergeRes.token
                  app.globalData.userInfo = mergeRes.user
                  app.globalData.isPremium = mergeRes.user.member_level === 'vip'
                  this.setData({ showBindPhoneModal: false, pendingToken: '', pendingUserInfo: null })
                  setTimeout(() => redirectAfterLogin(), 1500)
                } else {
                  wx.showToast({ title: mergeRes.error || '合并失败', icon: 'none' })
                }
              }
            }
          })
        } else {
          wx.showToast({ title: res.error || '绑定失败', icon: 'none' })
        }
      }
    } catch (e) {
      console.error('绑定手机号失败:', e)
      const errMsg = (typeof e === 'object') ? (e.error || e.message || '绑定失败') : e
      wx.showToast({ title: errMsg, icon: 'none' })
    } finally {
      this.setData({ bindLoading: false })
    }
  },

  /**
   * 开始绑定倒计时
   */
  startBindCountDown() {
    this.setData({
      bindCounting: true,
      bindCountDown: 60
    })

    const timer = setInterval(() => {
      const countDown = this.data.bindCountDown - 1
      if (countDown <= 0) {
        clearInterval(timer)
        this.setData({
          bindCounting: false,
          bindCountDown: 60,
          bindTimer: null
        })
      } else {
        this.setData({ bindCountDown: countDown })
      }
    }, 1000)

    this.setData({ bindTimer: timer })
  }
})
