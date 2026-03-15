/**
 * 发型迁移相关API
 */
import { post, get } from '../utils/request.js'

/**
 * 提取发型
 */
export function extractHair(data) {
    return post('/api/extract-hair', data, { timeout: 120000 }) // 2分钟超时
}

/**
 * 发型迁移（耗时操作，需要更长的超时时间）
 */
export function transferHair(data) {
    // 启用素描时需要更长的超时时间（5分钟）
    const timeout = data.enable_sketch ? 300000 : 120000
    // 添加 step_by_step 参数，支持分步模式
    const params = {
        ...data,
        step_by_step: data.step_by_step || false
    }
    return post('/api/transfer', params, { timeout: timeout })
}

/**
 * 在已有结果基础上生成素描
 * 支持分步处理：用户可以先进行发型迁移，然后再生成素描
 */
export function addSketch(data) {
    return post('/api/add-sketch', data, { timeout: 300000 }) // 5分钟超时
}

/**
 * 获取历史记录列表
 */
export function getHistoryList(page = 1, page_size = 10) {
    return get('/api/history/list', { page, page_size })
}

/**
 * 下载历史记录图片
 */
export function downloadHistoryImage(recordId) {
    return get('/api/history/download', { record_id: recordId })
}

export default {
    extractHair,
    transferHair,
    addSketch,
    getHistoryList,
    downloadHistoryImage
}
