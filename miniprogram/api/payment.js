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

// ==================== 微信虚拟支付（iOS端）====================

/**
 * 创建虚拟支付订单
 * @param {string} orderType - 'recharge' 或 'member'
 * @param {number} amount - 金额（元）
 * @param {string} goodsKey - 虚拟商品键
 */
export function createVirtualPayOrder(orderType, amount, goodsKey) {
  return post('/api/virtual-pay/create-order', {
    order_type: orderType,
    amount: amount,
    goods_key: goodsKey
  })
}

/**
 * 查询虚拟支付订单状态
 */
export function getVirtualPayOrderStatus(orderNo) {
  return get(`/api/virtual-pay/order-status/${orderNo}`)
}

/**
 * 调起微信虚拟支付
 * @param {Object} payParams - 后端返回的虚拟支付参数
 */
function requestVirtualPay(payParams) {
  return new Promise((resolve, reject) => {
    wx.openBusinessView({
      businessType: 'weappVirtualPay',
      extraData: {
        mch_id: payParams.mch_id,
        appid: payParams.appid,
        package: payParams.package,
        nonce_str: payParams.nonce_str,
        time_stamp: payParams.time_stamp,
        sign: payParams.sign,
        out_trade_no: payParams.out_trade_no,
        goods_id: payParams.goods_id,
        total_fee: payParams.total_fee
      },
      success: (res) => {
        resolve({ success: true, data: res })
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}

export default {
  getRechargeRules,
  createRechargeOrder,
  pay,
  getOrderStatus,
  getRechargeOrders,
  createVirtualPayOrder,
  getVirtualPayOrderStatus,
  requestVirtualPay
}
