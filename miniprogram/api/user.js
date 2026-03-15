/**
 * 用户相关API
 */

import { get, put, post } from '../utils/request.js'

/**
 * 获取用户信息
 */
export function getUserInfo() {
  return get('/api/user/info')
}

/**
 * 更新用户信息
 */
export function updateUserInfo(data) {
  return put('/api/user/update', data)
}

/**
 * 检查余额
 */
export function checkBalance() {
  return get('/api/consume/check')
}

/**
 * 获取消费记录
 */
export function getConsumptionRecords(page = 1, page_size = 20) {
  return get('/api/consume/records', { page, page_size })
}

export default {
  getUserInfo,
  updateUserInfo,
  checkBalance,
  getConsumptionRecords
}
