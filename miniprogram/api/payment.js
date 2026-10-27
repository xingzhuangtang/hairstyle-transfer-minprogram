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
 * 获取充值订单列表
 */
export function getRechargeOrders(page = 1, page_size = 20) {
  return get('/api/recharge/orders', { page, page_size })
}

// ==================== 微信虚拟支付（全平台）====================

/**
 * 通过 wx.login 获取 code，换取 session_key（虚拟支付签名用）
 */
export function getSessionKey() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (loginRes) => {
        if (!loginRes.code) {
          reject(new Error('wx.login 获取 code 失败'))
          return
        }
        post('/api/auth/get-session-key', { code: loginRes.code })
          .then((res) => {
            if (res.success && res.session_key) {
              resolve(res.session_key)
            } else {
              reject(new Error(res.error || '获取 session_key 失败'))
            }
          })
          .catch(reject)
      },
      fail: (err) => {
        const errMsg = err.errMsg || ''
        if (errMsg.includes('INVALID_LOGIN') || errMsg.includes('access_token expired')) {
          reject(new Error('微信登录态已过期，请关闭并重新打开微信开发者工具'))
        } else {
          reject(err)
        }
      }
    })
  })
}

/**
 * 创建虚拟支付订单
 * @param {string} orderType - 'recharge' 或 'member'
 * @param {number} amount - 金额（元）
 * @param {string} goodsKey - 虚拟商品键
 * @param {string} sessionKey - 从 wx.login 换取的 session_key
 * @param {number} env - 0=正式环境, 1=沙箱环境（开发者工具默认用沙箱）
 */
export function createVirtualPayOrder(orderType, amount, goodsKey, sessionKey, env = 0) {
  return post('/api/virtual-pay/create-order', {
    order_type: orderType,
    amount: amount,
    goods_key: goodsKey,
    session_key: sessionKey,
    env: env
  })
}

/**
 * 查询虚拟支付订单状态
 */
export function getVirtualPayOrderStatus(orderNo) {
  return get(`/api/virtual-pay/order-status/${orderNo}`)
}

/**
 * 前端支付成功后通知后端
 */
export function notifyVirtualPaySuccess(orderNo, transactionId) {
  return post('/api/virtual-pay/notify-success', {
    order_no: orderNo,
    transaction_id: transactionId
  })
}

/**
 * 调起微信虚拟支付（全平台）
 * @param {Object} payParams - 后端返回的虚拟支付参数
 * 参数格式：{ signData, pay_sig, signature, mode }
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
  getRechargeOrders,
  getSessionKey,
  createVirtualPayOrder,
  getVirtualPayOrderStatus,
  requestVirtualPay
}
