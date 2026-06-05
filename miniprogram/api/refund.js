import { get, post } from '../utils/request.js'

/**
 * 提交退款申请
 */
export function applyRefund(data) {
  return post('/api/refund/apply', data)
}

/**
 * 查询退款申请状态
 */
export function getRefundStatus(applicationId) {
  return get(`/api/refund/status/${applicationId}`)
}

/**
 * 获取退款申请列表
 */
export function getRefundApplications(page = 1, pageSize = 20) {
  return get('/api/refund/applications', { page, page_size: pageSize })
}
