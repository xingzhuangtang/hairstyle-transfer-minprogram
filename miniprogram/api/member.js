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

/**
 * 创建会员订单（Android 普通微信支付）
 * @param {string} paymentMethod - 支付方式 'wxpay'
 */
export function createMemberOrder(paymentMethod = 'wxpay') {
  return post('/api/member/buy', { payment_method: paymentMethod })
}

/**
 * 支付会员订单（获取微信支付参数）
 * @param {string} orderNo - 订单号
 * @param {string} paymentMethod - 支付方式 'wxpay'
 */
export function payMemberOrder(orderNo, paymentMethod = 'wxpay') {
  return post('/api/member/pay', { order_no: orderNo, payment_method: paymentMethod })
}

export default {
  getMemberInfo,
  getMemberOrders,
  createMemberOrder,
  payMemberOrder
}
