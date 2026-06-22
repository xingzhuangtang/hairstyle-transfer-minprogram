// api/customer.js - 客户档案 API 封装
import { get } from '../utils/request.js'

/**
 * 获取大盘数据（用户分布、资产总览）
 */
export function getDashboard() {
  return get('/api/dev/dashboard')
}

/**
 * 获取客户列表（分页、排序、筛选）
 * @param {Object} params - { page, page_size, sort_by, filter_level, filter_type }
 */
export function getCustomers(params) {
  return get('/api/dev/customers', params)
}

/**
 * 获取客户详情
 * @param {Number|String} id - 用户 ID
 */
export function getCustomerDetail(id) {
  return get(`/api/dev/customers/${id}`)
}

/**
 * 通过手机号精准查询客户
 * @param {String} phone - 手机号
 */
export function searchByPhone(phone) {
  return get('/api/dev/search', { phone })
}

/**
 * 获取今日动态统计
 */
export function getTodayStats() {
  return get('/api/dev/today')
}
