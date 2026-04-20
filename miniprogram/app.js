// app.js
import { API_BASE_URL } from './utils/constants.js'
import { getUserMode } from './utils/auth.js'

App({
  globalData: {
    userInfo: null,
    token: null,
    isPremium: false
  },

  onLaunch() {
    console.log('小程序启动')

    // 移除自动登录，让游客可以直接体验首页功能
    // 用户需要登录时再引导登录（符合微信审核要求）

    // 检查未完成订单（不阻塞页面加载，延迟执行）
    setTimeout(() => {
      this.checkPendingOrders()
    }, 1000)
  },

  onShow() {
    console.log('小程序显示')

    // 移除自动刷新用户信息，改为按需加载
    // 用户进入需要登录的页面时再引导登录
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
            title: '支付成功',
            content: '您的订单已支付完成',
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
              reject({ error: '请先登录', code: 401 })
              return
            }

            wx.reLaunch({
              url: '/pages/login/login'
            })
            reject({ error: '登录已过期，请重新登录' })
          } else {
            reject(res.data || { error: '请求失败' })
          }
        },
        fail: (err) => {
          console.error('网络请求失败:', err)
          reject({ error: '网络请求失败，请检查网络连接' })
        }
      })
    })
  },

  /**
   * 清除登录信息
   */
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
          title: '游客额度续期',
          content: `您的游客免费额度已续期，${res.hairs}根发丝已到账`,
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
  }
})
