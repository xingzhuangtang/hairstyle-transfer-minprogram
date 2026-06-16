// pages/profile/profile.js
import { getUser, isPremium, logout, refreshUserInfo, isDeveloperAccount, toggleVip, getDeveloperModeInstructions } from '../../utils/auth.js'
import { checkPremium, requireLogin } from '../../utils/auth.js'
import { MEMBER_LEVEL_NAMES, API_BASE_URL } from '../../utils/constants.js'
import { getUnreadCount } from '../../api/chat.js'

Page({
  data: {
    userInfo: {},
    isPremium: false,
    isDeveloper: false,
    memberLevelName: '普通用户',
    totalHairs: 0,
    daysRemaining: 0,
    toggleLoading: false,
    resetLoading: false,
    chatUnreadCount: 0,
    refundEnabled: false
  },

  onShow() {
    // 每次显示时刷新用户信息
    this.loadUserInfo()
    this.loadChatUnreadCount()
  },

  /**
   * 加载用户信息
   */
  async loadUserInfo() {
    try {
      const res = await refreshUserInfo()

      if (res.success && res.user) {
        const userInfo = res.user
        const isPremium = userInfo.member_level === 'vip'
        const isDeveloper = isDeveloperAccount()
        const totalHairs = (userInfo.scissor_hairs || 0) + (userInfo.comb_hairs || 0)

        // 计算剩余天数
        let daysRemaining = 0
        if (isPremium && userInfo.member_expire_at) {
          const expireTime = new Date(userInfo.member_expire_at)
          const now = new Date()
          const diffTime = expireTime - now
          daysRemaining = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
        }

        this.setData({
          userInfo: userInfo,
          isPremium: isPremium,
          isDeveloper: isDeveloper,
          memberLevelName: (typeof MEMBER_LEVEL_NAMES !== 'undefined' && MEMBER_LEVEL_NAMES[userInfo.member_level]) || '普通用户',
          totalHairs: totalHairs,
          daysRemaining: daysRemaining > 0 ? daysRemaining : 0,
          refundEnabled: userInfo.refund_enabled || false
        })
      } else {
        // 未登录，显示默认状态（不跳转登录页）
        this.setData({
          userInfo: {},
          isPremium: false,
          isDeveloper: false,
          memberLevelName: '游客',
          totalHairs: 0,
          daysRemaining: 0,
          refundEnabled: false
        })
      }
    } catch (e) {
      console.error('加载用户信息失败:', e)
      // 未登录，显示默认状态（不跳转登录页）
      this.setData({
        userInfo: {},
        isPremium: false,
        isDeveloper: false,
        memberLevelName: '游客',
        totalHairs: 0,
        daysRemaining: 0,
        refundEnabled: false
      })
    }
  },

  /**
   * 查看开发者模式说明
   */
  onViewDeveloperMode() {
    wx.showModal({
      title: '开发者模式',
      content: getDeveloperModeInstructions(),
      showCancel: false
    })
  },

  /**
   * 跳转到登录页
   */
  goToLogin() {
    wx.navigateTo({
      url: '/pages/login/login'
    })
  },

  /**
   * 跳转到历史记录
   */
  goToHistory() {
    if (!requireLogin()) {
      return
    }

    // 检查会员权限
    if (!checkPremium(true)) {
      return
    }

    wx.navigateTo({
      url: '/pages/history/history'
    })
  },

  /**
   * 跳转到消费记录
   */
  goToConsumption() {
    if (!requireLogin()) {
      return
    }

    wx.navigateTo({
      url: '/pages/consumption/consumption'
    })
  },

  /**
   * 跳转到充值中心
   */
  goToBalance() {
    if (!requireLogin()) {
      return
    }

    wx.navigateTo({
      url: '/pages/balance/balance'
    })
  },

  /**
   * 跳转到会员中心
   */
  goToMember() {
    if (!requireLogin()) {
      return
    }

    wx.navigateTo({
      url: '/pages/member/member'
    })
  },

  /**
   * 跳转到关于我们
   */
  goToAbout() {
    wx.navigateTo({
      url: '/pages/about/about'
    })
  },

  /**
   * 跳转到设备管理（游客和登录用户都可访问）
   */
  goToDevice() {
    wx.navigateTo({
      url: '/pages/device/device'
    })
  },

  /**
   * 跳转到设置
   */
  goToSettings() {
    if (!requireLogin()) {
      return
    }

    wx.navigateTo({
      url: '/pages/settings/settings'
    })
  },

  /**
   * 跳转到在线客服
   */
  goToChat() {
    wx.navigateTo({
      url: '/pages/chat/chat'
    })
  },

  /**
   * 加载聊天未读数
   */
  async loadChatUnreadCount() {
    try {
      const count = await getUnreadCount()
      this.setData({ chatUnreadCount: count || 0 })
    } catch (e) {
      // 静默失败，不影响主功能
    }
  },

  /**
   * 跳转到客户留言
   */
  goToMessage() {
    wx.navigateTo({
      url: '/pages/message/message'
    })
  },

  /**
   * 跳转到客户档案（开发者功能）
   */
  goToCustomerAdmin() {
    wx.navigateTo({
      url: '/pages/customer-admin/customer-admin'
    })
  },

  /**
   * 跳转到留言管理（开发者功能）
   */
  goToMessageAdmin() {
    wx.navigateTo({
      url: '/pages/message-admin/message-admin'
    })
  },

  /**
   * 跳转到退款权限管理（开发者功能）
   */
  goToRefundAdmin() {
    wx.navigateTo({
      url: '/pages/refund-admin/refund-admin'
    })
  },

  /**
   * 跳转到系统监控（开发者功能）
   */
  goToMonitor() {
    wx.navigateTo({
      url: '/pages/monitor/monitor'
    })
  },

  /**
   * 跳转到我的惊喜（推广返佣）
   */
  goToReferral() {
    wx.navigateTo({
      url: '/pages/referral/referral'
    })
  },

  /**
   * 跳转到退款申请
   */
  goToRefund() {
    wx.navigateTo({
      url: '/pages/refund/refund'
    })
  },

  /**
   * 退出登录
   */
  handleLogout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      confirmText: '确定',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          logout()
        }
      }
    })
  },

  /**
   * 清除数据重新测试（模拟新客户）
   */
  onResetForTest() {
    wx.showModal({
      title: '确认清除',
      content: '将清除当前账号的所有数据，重新以新客户身份体验。确定继续？',
      confirmText: '确定清除',
      cancelText: '取消',
      confirmColor: '#ff4d4f',
      success: (res) => {
        if (res.confirm) {
          this.doResetForTest()
        }
      }
    })
  },

  async doResetForTest() {
    this.setData({ resetLoading: true })

    try {
      // 1. 调用后端删除当前用户数据
      const app = getApp()
      const token = app.globalData.token || wx.getStorageSync('token')

      console.log('开始清除测试数据...')
      console.log('当前 token:', token ? token.substring(0, 20) + '...' : '无')

      if (token) {
        await new Promise((resolve, reject) => {
          const fullUrl = API_BASE_URL + '/api/dev/reset-test-user'
          console.log('调用后端删除接口:', fullUrl)

          wx.request({
            url: fullUrl,
            method: 'POST',
            header: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            success: (res) => {
              console.log('后端删除用户返回:', res.statusCode, res.data)
              if (res.statusCode === 200) {
                resolve(res.data)
              } else {
                reject(new Error(`后端删除失败: ${res.statusCode} - ${JSON.stringify(res.data)}`))
              }
            },
            fail: (err) => reject(new Error(`网络请求失败: ${JSON.stringify(err)}`))
          })
        })
      } else {
        console.warn('没有 token，跳过删除后端用户数据')
      }

      // 2. 清除本地存储和全局状态
      console.log('清除本地存储...')
      wx.removeStorageSync('token')
      wx.removeStorageSync('user_info')
      wx.removeStorageSync('userInfo')
      wx.removeStorageSync('pending_orders')
      app.globalData.token = null
      app.globalData.userInfo = null
      app.globalData.isPremium = false

      wx.showToast({
        title: '数据已清除，重新登录中...',
        icon: 'loading',
        duration: 2000
      })

      // 3. 使用 wx.reLaunch 重启小程序（会重新触发 onLaunch 和 guestAutoLogin）
      setTimeout(() => {
        console.log('重启小程序...')
        wx.reLaunch({
          url: '/pages/index/index'
        })
      }, 1000)
    } catch (e) {
      console.error('清除测试数据失败:', e)
      wx.showToast({
        title: '清除失败: ' + e.message,
        icon: 'none',
        duration: 3000
      })
    } finally {
      this.setData({ resetLoading: false })
    }
  },

  /**
   * 切换 VIP 状态（开发者功能）
   */
  async onToggleVip() {
    if (this.data.toggleLoading) {
      return
    }

    this.setData({ toggleLoading: true })

    try {
      const res = await toggleVip()

      if (res.success) {
        wx.showToast({
          title: res.message || '切换成功',
          icon: 'success'
        })

        // 刷新用户信息
        await this.loadUserInfo()
      } else {
        wx.showToast({
          title: res.error || '切换失败',
          icon: 'none'
        })
      }
    } catch (e) {
      console.error('切换 VIP 状态失败:', e)
      wx.showToast({
        title: e.error || '切换失败',
        icon: 'none'
      })
    } finally {
      this.setData({ toggleLoading: false })
    }
  }
})
