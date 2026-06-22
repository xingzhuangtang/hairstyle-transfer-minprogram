// app.js
import { API_BASE_URL } from './utils/constants.js'
import { getUserMode } from './utils/auth.js'
import { initLocale, onLocaleChange, getLocale } from './utils/i18n.js'

App({
  globalData: {
    userInfo: null,
    token: null,
    isPremium: false,
    locale: 'zh-CN'
  },

  onLaunch(options) {
    // 初始化语言偏好
    this.globalData.locale = initLocale()

    // 监听语言变更
    onLocaleChange((locale) => {
      this.globalData.locale = locale
      this.setTabBarLabels()
    })

    // 初始化 tabBar 标签
    this.setTabBarLabels()

    console.log('小程序启动')

    // 检查本地是否已有登录信息
    const token = wx.getStorageSync('token')
    if (!token) {
      // 无登录信息，自动游客静默登录
      this.guestAutoLogin()
    } else {
      // 已有 token，检查是否需要刷新用户信息
      this.refreshUserInfo()
    }

    // 检查推广扫码来源
    if (options && options.scene) {
      const scene = decodeURIComponent(options.scene)
      console.log('推广扫码来源:', scene)
      wx.setStorageSync('referral_scene', scene)
      // 等待登录后再追踪
      this.globalData.pendingReferralScene = scene
    }

    // 检查未完成订单（不阻塞页面加载，延迟执行）
    setTimeout(() => {
      this.checkPendingOrders()
    }, 1000)
  },

  onShow() {
    // 确保 globalData.locale 与 i18n 模块同步
    this.globalData.locale = getLocale()

    console.log('小程序显示')

    // 移除自动刷新用户信息，改为按需加载
    // 用户进入需要登录的页面时再引导登录
  },

  /**
   * 全局翻译函数
   */
  t(key, params) {
    const { t: translate } = require('./utils/i18n.js')
    return translate(key, params)
  },

  /**
   * 设置当前页面导航栏标题（基于当前语言）
   */
  setNavTitle(page, titleKey) {
    const title = this.t(titleKey)
    try {
      wx.setNavigationBarTitle({ title: title })
    } catch (e) {
      console.error('setNavTitle error:', e)
    }
  },

  /**
   * 动态设置 tabBar 文本（基于当前语言）
   */
  setTabBarLabels() {
    try {
      wx.setTabBarItem({
        index: 0,
        text: this.t('tabBar.home')
      })
      wx.setTabBarItem({
        index: 1,
        text: this.t('tabBar.profile')
      })
    } catch (e) {
      console.error('setTabBarLabels error:', e)
    }
  },

  /**
   * 检查未完成订单
   */
  async checkPendingOrders() {
    const pendingOrders = wx.getStorageSync('pending_orders') || []

    if (pendingOrders.length === 0) {
      return
    }

    console.log('检查未完成订单:', pendingOrders)

    // 检查每个订单的状态
    for (const orderNo of pendingOrders) {
      try {
        const res = await this.request({
          url: '/api/recharge/order/status',
          method: 'GET',
          data: { order_no: orderNo }
        })

        if (res.payment_status === 'success') {
          // 显示支付成功通知
          wx.showModal({
            title: this.t('app.paymentSuccess'),
            content: this.t('app.paymentSuccessContent'),
            showCancel: false,
            success: () => {
              // 刷新用户信息
              this.refreshUserInfo()
            }
          })

          // 移除已完成的订单
          const orders = wx.getStorageSync('pending_orders') || []
          wx.setStorageSync(
            'pending_orders',
            orders.filter(o => o !== orderNo)
          )
        }
      } catch (e) {
        console.error('检查订单状态失败:', e)
      }
    }
  },

  /**
   * 刷新用户信息
   */
  async refreshUserInfo() {
    try {
      const res = await this.request({
        url: '/api/user/info',
        method: 'GET',
        allowGuest: true
      })

      if (res.success) {
        this.globalData.userInfo = res.user
        this.globalData.isPremium = res.user.member_level === 'vip'
        wx.setStorageSync('user_info', res.user)

        // 判断用户模式
        const userMode = getUserMode(res.user)
        console.log('用户模式:', userMode)
      }
    } catch (e) {
      // 忽略错误（可能是未登录）
      console.log('刷新用户信息失败:', e)
    }
  },

  /**
   * 网络请求封装
   */
  request(options) {
    return new Promise((resolve, reject) => {
      const token = this.globalData.token || wx.getStorageSync('token')

      const header = {
        'Content-Type': 'application/json'
      }

      // 添加 Token
      if (token) {
        header['Authorization'] = `Bearer ${token}`
      }

      wx.request({
        url: API_BASE_URL + options.url,
        method: options.method || 'GET',
        data: options.data || {},
        header: {
          ...header,
          ...options.header
        },
        timeout: options.timeout || 30000,
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else if (res.statusCode === 401) {
            // Token 过期，清除登录信息
            this.clearLoginInfo()

            // 检查是否允许访客访问（不强制跳转登录页）
            if (options.allowGuest) {
              reject({ error: this.t('common.pleaseLogin'), code: 401 })
              return
            }

            wx.reLaunch({
              url: '/pages/login/login'
            })
            reject({ error: this.t('common.sessionExpired') })
          } else {
            reject(res.data || { error: this.t('common.requestFail') })
          }
        },
        fail: (err) => {
          console.error('网络请求失败:', err)
          reject({ error: this.t('common.networkRequestFail') })
        }
      })
    })
  },

  /**
   * 清除登录信息
   */
  /**
   * 游客自动静默登录
   * 首次进入自动调用微信登录，获取固定的用户 ID（用于追踪客户）
   */
  async guestAutoLogin() {
    try {
      const loginRes = await wx.login()
      if (!loginRes.code) {
        console.log('游客自动登录：获取code失败')
        return
      }

      // 获取设备信息（使用共享模块）
      const { getDeviceInfo } = await import('./utils/device.js')
      const deviceInfo = getDeviceInfo()

      // 调用后端微信登录接口，传递设备信息
      const res = await this.request({
        url: '/api/auth/wechat/login',
        method: 'POST',
        data: {
          code: loginRes.code,
          device_info: deviceInfo
        }
      })

      if (res.success && res.user) {
        // 保存 token 和用户信息
        wx.setStorageSync('token', res.token)
        wx.setStorageSync('user_info', res.user)
        this.globalData.token = res.token
        this.globalData.userInfo = res.user

        console.log('游客自动登录成功，账号 ID:', res.user.id, 'device_id:', res.user.device_id)

        // 检查是否有待处理的推广追踪
        this.trackPendingReferral()
      }
    } catch (e) {
      console.log('游客自动登录失败:', e)
    }
  },

  /**
   * 检查待处理的游客赠送
   */
  async checkPendingGuestBonus() {
    const userInfo = wx.getStorageSync('user_info')
    if (!userInfo || userInfo.user_type !== 'guest') {
      return
    }

    try {
      const res = await this.request({
        url: '/api/account/check-guest-bonus',
        method: 'POST',
        allowGuest: true
      })

      if (res.success && res.hairs) {
        wx.showModal({
          title: this.t('app.guestBonusTitle'),
          content: this.t('app.guestBonusContent', { hairs: res.hairs }),
          showCancel: false,
          success: () => {
            // 刷新用户信息
            this.refreshUserInfo()
          }
        })
      }
    } catch (e) {
      // 忽略错误（可能是没有待处理的赠送记录）
    }
  },

  clearLoginInfo() {
    this.globalData.token = null
    this.globalData.userInfo = null
    this.globalData.isPremium = false
    wx.removeStorageSync('token')
    wx.removeStorageSync('userInfo')
  },

  /**
   * 追踪待处理的推广来源
   */
  async trackPendingReferral() {
    const scene = this.globalData.pendingReferralScene
    if (!scene) {
      return
    }

    this.globalData.pendingReferralScene = null

    try {
      await this.request({
        url: '/api/referral/track',
        method: 'POST',
        data: { scene: scene },
        allowGuest: true
      })
      console.log('推广关系已追踪')
    } catch (e) {
      console.log('推广关系追踪失败:', e)
    }
  }
})
