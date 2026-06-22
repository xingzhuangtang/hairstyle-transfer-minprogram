/**
 * i18n 页面混入模块
 * 在每个页面的 Page 构造器中调用 loadI18n() 即可自动加载翻译到 data
 */
import { getLocale, onLocaleChange } from './i18n.js'

/**
 * 为页面加载翻译数据
 * @param {Page} page - 页面实例
 * @param {string[]} keys - 需要加载的翻译 key 数组，如 ['common.save', 'settings.avatar']
 * @param {string} prefix - data 字段前缀，默认 't'
 */
export function loadTranslations(page, keys, prefix = 't') {
  const app = getApp()
  const translations = {}
  keys.forEach(key => {
    const flatKey = key.replace(/\./g, '_')
    translations[`${prefix}${flatKey}`] = app.t(key)
  })
  page.setData(translations)
}

/**
 * 创建带 i18n 支持的页面配置
 * 用法：将原 Page({...}) 替换为 Page(createI18nPage({...}, ['common.save', 'index.hair']))
 */
export function createI18nPage(pageConfig, i18nKeys) {
  const originalOnLoad = pageConfig.onLoad
  const originalOnShow = pageConfig.onShow
  const originalOnUnload = pageConfig.onUnload

  pageConfig.onLoad = function(options) {
    this._i18nKeys = i18nKeys || []
    this._i18nLoaded = false
    this._loadI18n()
    if (originalOnLoad) originalOnLoad.call(this, options)
  }

  pageConfig.onShow = function() {
    this._loadI18n()
    if (originalOnShow) originalOnShow.call(this)
  }

  pageConfig.onUnload = function() {
    if (this._i18nUnbind) {
      this._i18nUnbind()
    }
    if (originalOnUnload) originalOnUnload.call(this)
  }

  pageConfig._loadI18n = function() {
    const locale = getLocale()
    if (this._i18nCurrentLocale === locale && this._i18nLoaded) return
    this._i18nCurrentLocale = locale
    loadTranslations(this, this._i18nKeys || [])
    this._i18nLoaded = true
  }

  return Page(pageConfig)
}
