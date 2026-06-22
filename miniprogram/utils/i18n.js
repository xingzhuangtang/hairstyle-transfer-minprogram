// 微信小程序不支持 import JSON，改用 require JS 模块
const zhCN = require('../i18n/zh-CN.js')
const enUS = require('../i18n/en-US.js')

const locales = {
  'zh-CN': zhCN,
  'en-US': enUS
}

const STORAGE_KEY = 'app_locale'
const DEFAULT_LOCALE = 'zh-CN'

let currentLocale = DEFAULT_LOCALE
let changeCallbacks = []

/**
 * 获取当前语言
 */
export function getLocale() {
  return currentLocale
}

/**
 * 设置语言并持久化
 */
export function setLocale(locale) {
  if (!locales[locale]) return
  currentLocale = locale
  try {
    wx.setStorageSync(STORAGE_KEY, locale)
  } catch (e) {
    console.error('setLocale storage error:', e)
  }
  changeCallbacks.forEach(cb => cb(locale))
}

/**
 * 初始化语言（从 storage 读取或使用默认）
 */
export function initLocale() {
  try {
    const saved = wx.getStorageSync(STORAGE_KEY)
    if (saved && locales[saved]) {
      currentLocale = saved
    }
  } catch (e) {
    console.error('initLocale error:', e)
  }
  return currentLocale
}

/**
 * 翻译函数
 */
export function t(key, params) {
  const messages = locales[currentLocale] || locales[DEFAULT_LOCALE]
  let text = key.split('.').reduce((obj, k) => obj && obj[k], messages)
  if (typeof text !== 'string') {
    return key
  }
  if (params) {
    Object.keys(params).forEach(k => {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), params[k])
    })
  }
  return text
}

/**
 * 注册语言变更回调
 */
export function onLocaleChange(callback) {
  changeCallbacks.push(callback)
}

/**
 * 获取所有支持的语言列表
 */
export function getSupportedLocales() {
  return Object.keys(locales)
}

/**
 * 获取语言的显示名称
 */
export function getLocaleDisplayName(locale) {
  const names = {
    'zh-CN': '中文',
    'en-US': 'English'
  }
  return names[locale] || locale
}
