/**
 * 支付相关API
 */

import { get, post } from '../utils/request.js'

/**
 * 获取充值规则
 */
export function getRechargeRules() {
  return get('/api/recharge/rules')
}

/**
 * 创建充值订单
 */
export function createRechargeOrder(amount, payment_method = 'wechat') {
  return post('/api/recharge/create-order', {
    amount: amount,
    payment_method: payment_method
  })
}

/**
 * 发起支付
 */
export function pay(order_no, payment_method = 'wechat') {
  return post('/api/recharge/pay', {
    order_no: order_no,
    payment_method: payment_method
  })
}

/**
 * 查询订单状态
 */
export function getOrderStatus(order_no) {
  return get('/api/recharge/order/status', { order_no })
}

/**
 * 获取充值订单列表
 */
export function getRechargeOrders(page = 1, page_size = 20) {
  return get('/api/recharge/orders', { page, page_size })
}

export default {
  getRechargeRules,
  createRechargeOrder,
  pay,
  getOrderStatus,
  getRechargeOrders
}
