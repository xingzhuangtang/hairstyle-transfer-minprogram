/**
 * 平台检测工具
 * 用于区分 iOS 和 Android 端，适配微信虚拟支付
 */

let _platform = null
let _systemInfo = null

/**
 * 获取系统信息（带缓存）
 */
function getSystemInfo() {
  if (!_systemInfo) {
    try {
      _systemInfo = wx.getSystemInfoSync()
    } catch (e) {
      console.error('获取系统信息失败:', e)
      _systemInfo = {}
    }
  }
  return _systemInfo
}

/**
 * 获取当前平台
 * @returns {string} 'ios' | 'android' | 'devtools'
 */
function getPlatform() {
  if (!_platform) {
    const systemInfo = getSystemInfo()
    const system = (systemInfo.system || '').toLowerCase()

    if (system.indexOf('ios') !== -1) {
      _platform = 'ios'
    } else if (system.indexOf('android') !== -1) {
      _platform = 'android'
    } else if (system.indexOf('devtools') !== -1 || system.indexOf('mac') !== -1 || system.indexOf('windows') !== -1) {
      // 开发者工具
      _platform = 'devtools'
    } else {
      _platform = 'unknown'
    }
  }
  return _platform
}

/**
 * 是否为 iOS 平台
 */
function isIOS() {
  return getPlatform() === 'ios'
}

/**
 * 是否为 Android 平台
 */
function isAndroid() {
  return getPlatform() === 'android'
}

/**
 * 是否为微信开发者工具
 */
function isDevTools() {
  return getPlatform() === 'devtools'
}

/**
 * 是否需要使用虚拟支付
 * iOS 端需要使用微信虚拟支付，Android 使用普通微信支付
 */
function needsVirtualPay() {
  const platform = getPlatform()
  // iOS 需要虚拟支付
  // 开发者工具可以跳过，用于测试
  return platform === 'ios'
}

/**
 * 获取虚拟商品键
 * @param {string} type - 'recharge' 或 'member'
 * @param {number} amount - 金额（充值时）
 * @returns {string} 虚拟商品键
 */
function getVirtualGoodsKey(type, amount) {
  if (type === 'recharge') {
    return `recharge_${amount}`
  } else if (type === 'member') {
    return 'member_vip'
  }
  return ''
}

module.exports = {
  getPlatform,
  isIOS,
  isAndroid,
  isDevTools,
  needsVirtualPay,
  getVirtualGoodsKey,
  getSystemInfo
}
