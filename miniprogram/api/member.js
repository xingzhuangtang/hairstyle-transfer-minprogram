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
 * 购买会员
 */
export function buyMember(payment_method = 'wechat') {
  return post('/api/member/buy', {
    payment_method: payment_method
  })
}

/**
 * 支付会员订单
 */
export function payMemberOrder(order_no, payment_method = 'wechat') {
  return post('/api/member/pay', {
    order_no: order_no,
    payment_method: payment_method
  })
}

/**
 * 获取会员订单列表
 */
export function getMemberOrders(page = 1, page_size = 20) {
  return get('/api/member/orders', { page, page_size })
}

export default {
  getMemberInfo,
  buyMember,
  payMemberOrder,
  getMemberOrders
}
