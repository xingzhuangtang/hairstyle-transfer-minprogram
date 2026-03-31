// pages/profile/profile.js
import { getUser, isPremium, logout, refreshUserInfo, isDeveloperAccount, toggleVip } from '../../utils/auth.js'
import { checkPremium, requireLogin } from '../../utils/auth.js'
import { MEMBER_LEVEL_NAMES } from '../../utils/constants.js'

Page({
  data: {
    userInfo: {},
    isPremium: false,
    isDeveloper: false,
    memberLevelName: '普通用户',
    totalHairs: 0,
    daysRemaining: 0,
    toggleLoading: false
  },

  onShow() {
    // 每次显示时刷新用户信息
    this.loadUserInfo()
  },

  /**
   * 加载用户信息
   */
  async loadUserInfo() {
    try {
      const res = await refreshUserInfo()

      if (res.success) {
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
          daysRemaining: daysRemaining > 0 ? daysRemaining : 0
        })
      }
    } catch (e) {
      console.error('加载用户信息失败:', e)

      // 如果未登录，跳转到登录页
      if (e.code === 401) {
        wx.reLaunch({
          url: '/pages/login/login'
        })
      }
    }
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
    wx.showModal({
      title: '关于我们',
      content: '发型迁移 v1.0.0\n基于AI的发型虚拟试戴应用',
      showCancel: false
    })
  },

  /**
   * 跳转到设置
   */
  goToSettings() {
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
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
