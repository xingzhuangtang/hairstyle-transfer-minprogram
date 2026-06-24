/**
 * 网络请求封装
 * 提供统一的 HTTP 请求接口，自动处理 Token、错误等
 */

import { API_BASE_URL } from './constants.js'
import { getToken, clearAuthInfo } from './storage.js'
import { getDeviceId } from './device.js'

/**
 * 网络请求基础函数
 */
function request(options) {
  return new Promise((resolve, reject) => {
    // 获取 Token
    const token = getToken()

    // 构建请求头
    const header = {
      'Content-Type': 'application/json',
      'X-Device-ID': getDeviceId()  // 始终附加设备 ID
    }

    // 添加 Token
    if (token) {
      header['Authorization'] = `Bearer ${token}`
    }

    // 合并自定义请求头
    if (options.header) {
      Object.assign(header, options.header)
    }

    // 发起请求
    console.log('[wx.request] 发起请求:', API_BASE_URL + options.url)
    wx.request({
      url: API_BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: header,
      timeout: options.timeout || 30000,
      dataType: options.dataType || 'json',
      success: (res) => {
        // HTTP 状态码 200
        if (res.statusCode === 200) {
          resolve(res.data)
        }
        // 401 未授权
        else if (res.statusCode === 401) {
          console.error('Token 已过期或无效')

          // 清除认证信息
          clearAuthInfo()

          const t = (key) => getApp().t(key)

          // 检查是否允许访客访问（不强制跳转登录页）
          if (options.allowGuest) {
            reject({
              error: t('common.pleaseLogin'),
              code: 401,
              needLogin: true
            })
            return
          }

          // 跳转到登录页
          const pages = getCurrentPages()
          const currentPage = pages[pages.length - 1]
          const currentUrl = '/' + currentPage.route

          // 保存当前路径
          if (currentUrl !== '/pages/login/login') {
            wx.setStorageSync('redirect_url', currentUrl)
          }

          // 跳转登录
          wx.reLaunch({
            url: '/pages/login/login'
          })

          reject({
            error: t('common.sessionExpired'),
            code: 401
          })
        }
        // 403 禁止访问
        else if (res.statusCode === 403) {
          const t = (key) => getApp().t(key)
          reject({
            error: res.data.error || t('common.noPermission'),
            code: 403
          })
        }
        // 404 未找到
        else if (res.statusCode === 404) {
          reject({
            error: getApp().t('common.resourceNotFound'),
            code: 404
          })
        }
        // 500 服务器错误
        else if (res.statusCode >= 500) {
          reject({
            error: getApp().t('common.serverError'),
            code: res.statusCode
          })
        }
        // 其他错误
        else {
          const t = (key) => getApp().t(key)
          reject({
            error: res.data.error || res.data.message || t('common.requestFail'),
            code: res.statusCode,
            data: res.data
          })
        }
      },
      fail: (err) => {
        console.error('[wx.request fail] 错误:', err)
        console.error('网络请求失败:', err)

        const t = (key) => getApp().t(key)

        // 判断错误类型
        let errorMsg = t('common.networkRequestFail')

        if (err.errMsg.includes('timeout')) {
          errorMsg = t('common.requestTimeout')
        } else if (err.errMsg.includes('fail')) {
          errorMsg = t('common.networkDisconnected')
        }

        reject({
          error: errorMsg,
          detail: err.errMsg
        })
      }
    })
  })
}

/**
 * GET 请求
 */
export function get(url, data = {}, options = {}) {
  return request({
    url: url,
    method: 'GET',
    data: data,
    ...options
  })
}

/**
 * POST 请求
 */
export function post(url, data = {}, options = {}) {
  console.log('[POST] 请求 URL:', url)
  console.log('[POST] 请求数据:', data)
  return request({
    url: url,
    method: 'POST',
    data: data,
    ...options
  })
}

/**
 * PUT 请求
 */
export function put(url, data = {}, options = {}) {
  return request({
    url: url,
    method: 'PUT',
    data: data,
    ...options
  })
}

/**
 * DELETE 请求
 */
export function del(url, data = {}, options = {}) {
  return request({
    url: url,
    method: 'DELETE',
    data: data,
    ...options
  })
}

/**
 * 上传文件
 */
export function uploadFile(filePath, formData = {}) {
  return new Promise((resolve, reject) => {
    const token = getToken()

    const header = {}

    // 添加 Token
    if (token) {
      header['Authorization'] = `Bearer ${token}`
    } else {
      // 没有 token 时，传递 allowGuest 标志
      formData.allowGuest = true
    }

    wx.uploadFile({
      url: API_BASE_URL + '/api/upload',
      filePath: filePath,
      name: 'file',
      formData: formData,
      header: header,
      timeout: 60000,
      success: (res) => {
        console.log('[wx.request success] 响应 statusCode:', res.statusCode, 'data:', res.data)
        const t = (key) => getApp().t(key)
        if (res.statusCode === 200) {
          try {
            const data = JSON.parse(res.data)
            resolve(data)
          } catch (e) {
            reject({
              error: t('common.parseResponseFail')
            })
          }
        } else if (res.statusCode === 401) {
          // 访客模式下不强制跳转
          if (formData.allowGuest) {
            clearAuthInfo()
            reject({
              error: t('common.pleaseLogin'),
              code: 401,
              needLogin: true
            })
            return
          }
          clearAuthInfo()
          wx.reLaunch({
            url: '/pages/login/login'
          })
          reject({
            error: t('common.sessionExpired'),
            code: 401
          })
        } else {
          reject({
            error: t('common.uploadFail'),
            code: res.statusCode
          })
        }
      },
      fail: (err) => {
        console.error('上传文件失败:', err)
        reject({
          error: getApp().t('common.uploadFailNetwork')
        })
      }
    })
  })
}

/**
 * 下载文件
 */
export function downloadFile(url) {
  return new Promise((resolve, reject) => {
    wx.downloadFile({
      url: url,
      timeout: 60000,
      success: (res) => {
        console.log('[wx.request success] 响应 statusCode:', res.statusCode, 'data:', res.data)
        if (res.statusCode === 200) {
          resolve(res.tempFilePath)
        } else {
          reject({
            error: getApp().t('common.downloadFailNetwork'),
            code: res.statusCode
          })
        }
      },
      fail: (err) => {
        console.error('下载文件失败:', err)
        reject({
          error: getApp().t('common.downloadFailNetwork')
        })
      }
    })
  })
}

export default {
  get,
  post,
  put,
  del,
  uploadFile,
  downloadFile
}
