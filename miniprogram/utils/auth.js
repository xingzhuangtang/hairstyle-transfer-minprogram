/**
 * 认证管理
 * 提供登录、登出、权限检查等功能
 */

import { post, get } from './request.js'
import { setToken, getToken, setUserInfo, getUserInfo, clearAuthInfo, setRedirectUrl, getRedirectUrl } from './storage.js'

/**
 * 检查登录状态
 */
export function checkLogin() {
  const token = getToken()
  const userInfo = getUserInfo()
  return !!(token && userInfo)
}

/**
 * 检查是否为会员
 */
export function isPremium() {
  const userInfo = getUserInfo()
  return userInfo && userInfo.member_level === 'vip'
}

/**
 * 获取用户信息
 */
export function getUser() {
  return getUserInfo()
}

/**
 * 微信登录
 */
export async function wechatLogin() {
  try {
    // 1. 获取code
    const loginRes = await wx.login()

    if (!loginRes.code) {
      throw new Error('获取微信code失败')
    }

    // 2. 调用后端API
    const res = await post('/api/auth/wechat/login', {
      code: loginRes.code
    })

    if (res.success) {
      // 3. 保存Token和用户信息
      setToken(res.token)
      setUserInfo(res.user)

      // 4. 更新全局数据
      const app = getApp()
      app.globalData.token = res.token
      app.globalData.userInfo = res.user
      app.globalData.isPremium = res.user.member_level === 'vip'

      return {
        success: true,
        user: res.user
      }
    } else {
      return {
        success: false,
        error: res.error || '登录失败'
      }
    }
  } catch (e) {
    console.error('微信登录失败:', e)
    return {
      success: false,
      error: e.error || e.message || '登录失败'
    }
  }
}

/**
 * 手机号登录
 */
export async function phoneLogin(phone, code) {
  try {
    const res = await post('/api/auth/phone/login', {
      phone: phone,
      code: code
    })

    if (res.success) {
      // 保存Token和用户信息
      setToken(res.token)
      setUserInfo(res.user)

      // 更新全局数据
      const app = getApp()
      app.globalData.token = res.token
      app.globalData.userInfo = res.user
      app.globalData.isPremium = res.user.member_level === 'vip'

      return {
        success: true,
        user: res.user
      }
    } else {
      return {
        success: false,
        error: res.error || '登录失败'
      }
    }
  } catch (e) {
    console.error('手机号登录失败:', e)
    return {
      success: false,
      error: e.error || e.message || '登录失败'
    }
  }
}

/**
 * 发送验证码
 */
export async function sendVerificationCode(phone) {
  try {
    const res = await post('/api/auth/phone/send-code', {
      phone: phone
    })

    console.log('发送验证码返回:', res)

    return {
      success: res.success,
      error: res.error,
      code: res.code,  // 测试模式下返回验证码
      expire_time: res.expire_time,
      test_mode: res.test_mode
    }
  } catch (e) {
    console.error('发送验证码失败:', e)
    return {
      success: false,
      error: e.error || e.message || '发送失败'
    }
  }
}

/**
 * 绑定手机号
 */
export async function bindPhone(phone, code) {
  try {
    const res = await post('/api/auth/bind-phone', {
      phone: phone,
      verification_code: code
    })

    if (res.success) {
      // 更新用户信息
      setUserInfo(res.user)

      const app = getApp()
      app.globalData.userInfo = res.user

      return {
        success: true,
        user: res.user
      }
    } else {
      return {
        success: false,
        error: res.error || '绑定失败'
      }
    }
  } catch (e) {
    console.error('绑定手机号失败:', e)
    return {
      success: false,
      error: e.error || e.message || '绑定失败'
    }
  }
}

/**
 * 退出登录
 */
export function logout() {
  // 清除本地存储
  clearAuthInfo()

  // 清除全局数据
  const app = getApp()
  app.globalData.token = null
  app.globalData.userInfo = null
  app.globalData.isPremium = false

  // 跳转到登录页
  wx.reLaunch({
    url: '/pages/login/login'
  })
}

/**
 * 检查会员权限
 * 如果不是会员，显示升级提示
 */
export function checkPremium(showTip = true) {
  if (isPremium()) {
    return true
  }

  if (showTip) {
    wx.showModal({
      title: '升级会员',
      content: '此功能仅限陪跑会员使用，升级后即可享受50%折扣特权',
      confirmText: '立即升级',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          wx.navigateTo({
            url: '/pages/member/member'
          })
        }
      }
    })
  }

  return false
}

/**
 * 刷新用户信息
 */
export async function refreshUserInfo() {
  try {
    const res = await get('/api/user/info')

    if (res.success) {
      setUserInfo(res.user)

      const app = getApp()
      app.globalData.userInfo = res.user
      app.globalData.isPremium = res.user.member_level === 'vip'

      return {
        success: true,
        user: res.user
      }
    } else {
      return {
        success: false,
        error: res.error || '刷新失败'
      }
    }
  } catch (e) {
    console.error('刷新用户信息失败:', e)
    // 401 错误表示未登录，返回特定错误码
    if (e && e.code === 401) {
      return {
        success: false,
        error: '请先登录',
        code: 401,
        needLogin: true
      }
    }
    return {
      success: false,
      error: e.error || e.message || '刷新失败'
    }
  }
}

/**
 * 检查登录并提示
 * 如果未登录，显示可选登录提示（不强制跳转）
 * @param {string} action - 需要登录才能执行的操作描述
 * @returns {Promise<boolean>} - 用户是否选择登录
 */
export function optionalLogin(action = '使用此功能') {
  return new Promise((resolve) => {
    if (!checkLogin()) {
      wx.showModal({
        title: '提示',
        content: `登录后即可${action}，是否立即登录？`,
        confirmText: '去登录',
        cancelText: '暂不',
        success: (res) => {
          if (res.confirm) {
            // 保存当前路径
            const pages = getCurrentPages()
            const currentPage = pages[pages.length - 1]
            const currentUrl = '/' + currentPage.route
            setRedirectUrl(currentUrl)

            wx.navigateTo({
              url: '/pages/login/login'
            })
            resolve(false)
          } else {
            resolve(false)
          }
        },
        fail: () => {
          resolve(false)
        }
      })
      return
    }
    resolve(true)
  })
}

/**
 * 检查登录并跳转
 * 如果未登录，跳转到登录页（用于必须登录的场景）
 */
export function requireLogin() {
  if (!checkLogin()) {
    // 保存当前路径
    const pages = getCurrentPages()
    const currentPage = pages[pages.length - 1]
    const currentUrl = '/' + currentPage.route

    setRedirectUrl(currentUrl)

    // 跳转登录
    wx.navigateTo({
      url: '/pages/login/login'
    })

    return false
  }

  return true
}

/**
 * 登录成功后跳转
 */
export function redirectAfterLogin() {
  const redirectUrl = getRedirectUrl()

  if (redirectUrl) {
    // 返回之前的页面
    wx.redirectTo({
      url: redirectUrl,
      fail: () => {
        // 如果页面不存在，跳转到首页
        wx.switchTab({
          url: '/pages/index/index'
        })
      }
    })
  } else {
    // 跳转到首页
    wx.switchTab({
      url: '/pages/index/index'
    })
  }
}

/**
 * 检查是否为开发者账号
 */
export function isDeveloperAccount() {
  const userInfo = getUserInfo()
  // 开发者账号 ID 列表
  const developerIds = [5, 7]
  return userInfo && userInfo.id && developerIds.includes(userInfo.id)
}

/**
 * 切换会员状态（开发者功能）
 */
export async function toggleVip() {
  try {
    const res = await post('/api/dev/toggle-vip', {})

    if (res.success) {
      // 更新本地存储的用户信息
      setUserInfo(res.user)

      // 更新全局数据
      const app = getApp()
      app.globalData.userInfo = res.user
      app.globalData.isPremium = res.user.member_level === 'vip'

      return {
        success: true,
        user: res.user,
        message: res.message
      }
    } else {
      return {
        success: false,
        error: res.error || '切换失败'
      }
    }
  } catch (e) {
    console.error('切换会员状态失败:', e)
    return {
      success: false,
      error: e.error || e.message || '切换失败'
    }
  }
}

export default {
  checkLogin,
  isPremium,
  isDeveloperAccount,
  getUser,
  wechatLogin,
  phoneLogin,
  sendVerificationCode,
  bindPhone,
  logout,
  checkPremium,
  refreshUserInfo,
  requireLogin,
  optionalLogin,
  redirectAfterLogin,
  toggleVip
}
