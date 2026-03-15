/**
 * 本地存储封装
 * 提供统一的本地存储操作接口
 */

import { STORAGE_KEYS } from './constants.js'

/**
 * 设置Token
 */
export function setToken(token) {
  try {
    wx.setStorageSync(STORAGE_KEYS.TOKEN, token)
    return true
  } catch (e) {
    console.error('设置Token失败:', e)
    return false
  }
}

/**
 * 获取Token
 */
export function getToken() {
  try {
    return wx.getStorageSync(STORAGE_KEYS.TOKEN)
  } catch (e) {
    console.error('获取Token失败:', e)
    return null
  }
}

/**
 * 移除Token
 */
export function removeToken() {
  try {
    wx.removeStorageSync(STORAGE_KEYS.TOKEN)
    return true
  } catch (e) {
    console.error('移除Token失败:', e)
    return false
  }
}

/**
 * 设置用户信息
 */
export function setUserInfo(userInfo) {
  try {
    wx.setStorageSync(STORAGE_KEYS.USER_INFO, userInfo)
    return true
  } catch (e) {
    console.error('设置用户信息失败:', e)
    return false
  }
}

/**
 * 获取用户信息
 */
export function getUserInfo() {
  try {
    return wx.getStorageSync(STORAGE_KEYS.USER_INFO)
  } catch (e) {
    console.error('获取用户信息失败:', e)
    return null
  }
}

/**
 * 移除用户信息
 */
export function removeUserInfo() {
  try {
    wx.removeStorageSync(STORAGE_KEYS.USER_INFO)
    return true
  } catch (e) {
    console.error('移除用户信息失败:', e)
    return false
  }
}

/**
 * 清除所有认证信息
 */
export function clearAuthInfo() {
  try {
    removeToken()
    removeUserInfo()
    return true
  } catch (e) {
    console.error('清除认证信息失败:', e)
    return false
  }
}

/**
 * 添加未完成订单
 */
export function addPendingOrder(orderNo) {
  try {
    const orders = wx.getStorageSync(STORAGE_KEYS.PENDING_ORDERS) || []
    if (!orders.includes(orderNo)) {
      orders.push(orderNo)
      wx.setStorageSync(STORAGE_KEYS.PENDING_ORDERS, orders)
    }
    return true
  } catch (e) {
    console.error('添加未完成订单失败:', e)
    return false
  }
}

/**
 * 移除未完成订单
 */
export function removePendingOrder(orderNo) {
  try {
    const orders = wx.getStorageSync(STORAGE_KEYS.PENDING_ORDERS) || []
    const newOrders = orders.filter(o => o !== orderNo)
    wx.setStorageSync(STORAGE_KEYS.PENDING_ORDERS, newOrders)
    return true
  } catch (e) {
    console.error('移除未完成订单失败:', e)
    return false
  }
}

/**
 * 获取未完成订单列表
 */
export function getPendingOrders() {
  try {
    return wx.getStorageSync(STORAGE_KEYS.PENDING_ORDERS) || []
  } catch (e) {
    console.error('获取未完成订单失败:', e)
    return []
  }
}

/**
 * 设置重定向URL
 */
export function setRedirectUrl(url) {
  try {
    wx.setStorageSync(STORAGE_KEYS.REDIRECT_URL, url)
    return true
  } catch (e) {
    console.error('设置重定向URL失败:', e)
    return false
  }
}

/**
 * 获取重定向URL
 */
export function getRedirectUrl() {
  try {
    const url = wx.getStorageSync(STORAGE_KEYS.REDIRECT_URL)
    removeRedirectUrl()
    return url
  } catch (e) {
    console.error('获取重定向URL失败:', e)
    return null
  }
}

/**
 * 移除重定向URL
 */
export function removeRedirectUrl() {
  try {
    wx.removeStorageSync(STORAGE_KEYS.REDIRECT_URL)
    return true
  } catch (e) {
    console.error('移除重定向URL失败:', e)
    return false
  }
}

/**
 * 通用存储方法
 */
export function setStorage(key, value) {
  try {
    wx.setStorageSync(key, value)
    return true
  } catch (e) {
    console.error('存储数据失败:', e)
    return false
  }
}

/**
 * 通用获取方法
 */
export function getStorage(key) {
  try {
    return wx.getStorageSync(key)
  } catch (e) {
    console.error('获取数据失败:', e)
    return null
  }
}

/**
 * 通用移除方法
 */
export function removeStorage(key) {
  try {
    wx.removeStorageSync(key)
    return true
  } catch (e) {
    console.error('移除数据失败:', e)
    return false
  }
}

/**
 * 清空所有存储
 */
export function clearStorage() {
  try {
    wx.clearStorageSync()
    return true
  } catch (e) {
    console.error('清空存储失败:', e)
    return false
  }
}

/**
 * 获取存储信息
 */
export function getStorageInfo() {
  try {
    return wx.getStorageInfoSync()
  } catch (e) {
    console.error('获取存储信息失败:', e)
    return null
  }
}
