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
        user: res.user,
        isGuest: res.is_guest
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
 * 游客静默登录（自动接待）
 * 首次进入：游客模式（赠送 198 根梳子发丝）
 * 已绑定微信/手机：普通用户模式
 * 已购买 VIP：会员模式
 */
export async function guestLogin() {
  try {
    // 1. 获取 code
    const loginRes = await wx.login()

    if (!loginRes.code) {
      throw new Error('获取微信 code 失败')
    }

    // 2. 调用后端 API（后端根据 user_type 和 member_level 自动判断用户模式）
    const res = await post('/api/auth/wechat/login', {
      code: loginRes.code
    })

    if (res.success) {
      // 3. 保存 Token 和用户信息
      setToken(res.token)
      setUserInfo(res.user)

      // 4. 更新全局数据
      const app = getApp()
      app.globalData.token = res.token
      app.globalData.userInfo = res.user
      app.globalData.isPremium = res.user.member_level === 'vip'

      // 5. 判断用户模式
      const userMode = getUserMode(res.user)
      console.log('自动登录成功:', {
        user_type: res.user.user_type,
        member_level: res.user.member_level,
        userMode: userMode
      })

      return {
        success: true,
        user: res.user,
        userMode: userMode,  // guest, normal, vip
        isNewGuest: res.is_new_user && res.user.user_type === 'guest'
      }
    } else {
      return {
        success: false,
        error: res.error || '登录失败'
      }
    }
  } catch (e) {
    console.error('游客登录失败:', e)
    return {
      success: false,
      error: e.error || e.message || '登录失败'
    }
  }
}

/**
 * 判断用户模式
 * @param {Object} user - 用户信息
 * @returns {string} - 'guest' | 'normal' | 'vip'
 */
export function getUserMode(user) {
  if (!user) return 'guest'

  // 游客模式：user_type='guest'
  if (user.user_type === 'guest') {
    return 'guest'
  }

  // 会员模式：member_level='vip'
  if (user.member_level === 'vip') {
    return 'vip'
  }

  // 普通用户模式：user_type='registered' 且 member_level='normal'
  return 'normal'
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
    // 使用 allowGuest: true 允许访客访问
    const res = await get('/api/user/info', {}, { allowGuest: true })

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
 * 开发者模式通过环境变量控制，前端无法主动切换
 * 仅用于显示开发者专属功能入口（如果后端启用）
 *
 * 注意：后端 to_dict() 不返回 is_developer 字段，所以此函数始终返回 false
 */
export function isDeveloperAccount() {
  // 开发者模式完全由后端环境变量控制
  // 前端仅读取用户信息中的 developer 标志（如果后端返回）
  // 由于后端没有返回 is_developer 字段，所以始终为 false
  const userInfo = getUserInfo()

  // 调试日志
  console.log('isDeveloperAccount check:', {
    hasUserInfo: !!userInfo,
    is_developer: userInfo ? userInfo.is_developer : undefined,
    result: !!(userInfo && userInfo.is_developer === true)
  })

  return userInfo && userInfo.is_developer === true
}

/**
 * 开发者模式激活说明
 * 开发者模式必须通过配置 DEVELOPER_MODE_ENABLED=true 和 DEVELOPER_ACCOUNTS 来启用
 */
export function getDeveloperModeInstructions() {
  return '开发者模式需联系管理员配置，无法自行切换'
}

/**
 * 切换会员状态（开发者功能）
 * 注意：此功能仅在开发者模式启用时可用
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
  getDeveloperModeInstructions,
  getUser,
  getUserMode,
  wechatLogin,
  guestLogin,
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
