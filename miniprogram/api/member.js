/**
 * 会员相关 API
 */

import { get, post } from '../utils/request.js'

/**
 * 获取会员信息
 */
export function getMemberInfo() {
  return get('/api/member/info')
}

/**
 * 获取会员订单列表
 */
export function getMemberOrders(page = 1, page_size = 20) {
  return get('/api/member/orders', { page, page_size })
}

export default {
  getMemberInfo,
  getMemberOrders
}
