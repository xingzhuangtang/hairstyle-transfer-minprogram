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
 * 获取用户 session_key（从 wx.login 获取）
 */
export function getSessionKey() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (res) => {
        if (res.code) {
          // 调用后端接口，用 code 换取 session_key
          post('/api/auth/get-session-key', { code: res.code })
            .then(result => {
              if (result.success) {
                resolve(result.session_key)
              } else {
                reject(new Error(result.error || '获取 session_key 失败'))
              }
            })
            .catch(reject)
        } else {
          reject(new Error('wx.login 失败: ' + res.errMsg))
        }
      },
      fail: reject
    })
  })
}

/**
 * 创建虚拟支付订单
 * @param {string} orderType - 'recharge' 或 'member'
 * @param {number} amount - 金额（元）
 * @param {string} goodsKey - 虚拟商品键
 * @param {string} sessionKey - 用户 session_key
 */
export function createVirtualPayOrder(orderType, amount, goodsKey, sessionKey) {
  return post('/api/virtual-pay/create-order', {
    order_type: orderType,
    amount: amount,
    goods_key: goodsKey,
    session_key: sessionKey
  })
}

/**
 * 查询虚拟支付订单状态
 */
export function getVirtualPayOrderStatus(orderNo) {
  return get(`/api/virtual-pay/order-status/${orderNo}`)
}

/**
 * 调起微信虚拟支付（使用官方 wx.requestVirtualPayment API）
 * @param {Object} payParams - 后端返回的虚拟支付参数
 * @param {string} payParams.signData - signData JSON 字符串
 * @param {string} payParams.paySig - 支付签名
 * @param {string} payParams.signature - 用户态签名
 * @param {string} payParams.mode - 支付类型（short_series_goods 或 short_series_coin）
 */
export function requestVirtualPay(payParams) {
  return new Promise((resolve, reject) => {
    wx.requestVirtualPayment({
      signData: payParams.signData,
      paySig: payParams.pay_sig,
      signature: payParams.signature,
      mode: payParams.mode || 'short_series_goods',
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
