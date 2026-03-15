/**
 * 认证相关API
 */

import { post, get } from '../utils/request.js'

/**
 * 微信登录
 */
export function wechatLogin(code) {
  return post('/api/auth/wechat/login', { code })
}

/**
 * 发送短信验证码
 */
export function sendCode(phone) {
  return post('/api/auth/phone/send-code', { phone })
}

/**
 * 手机号登录
 */
export function phoneLogin(phone, code) {
  return post('/api/auth/phone/login', {
    phone: phone,
    verification_code: code
  })
}

/**
 * 绑定手机号
 */
export function bindPhone(phone, code) {
  return post('/api/auth/bind-phone', {
    phone: phone,
    verification_code: code
  })
}

export default {
  wechatLogin,
  sendCode,
  phoneLogin,
  bindPhone
}
