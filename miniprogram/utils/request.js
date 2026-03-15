/**
 * 网络请求封装
 * 提供统一的HTTP请求接口，自动处理Token、错误等
 */

import { API_BASE_URL } from './constants.js'
import { getToken, clearAuthInfo } from './storage.js'

/**
 * 网络请求基础函数
 */
function request(options) {
  return new Promise((resolve, reject) => {
    // 获取Token
    const token = getToken()

    // 构建请求头
    const header = {
      'Content-Type': 'application/json'
    }

    // 添加Token
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
        // HTTP状态码200
        if (res.statusCode === 200) {
          resolve(res.data)
        }
        // 401 未授权
        else if (res.statusCode === 401) {
          console.error('Token已过期或无效')

          // 清除认证信息
          clearAuthInfo()

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
            error: '登录已过期，请重新登录',
            code: 401
          })
        }
        // 403 禁止访问
        else if (res.statusCode === 403) {
          reject({
            error: res.data.error || '无权限访问',
            code: 403
          })
        }
        // 404 未找到
        else if (res.statusCode === 404) {
          reject({
            error: '请求的资源不存在',
            code: 404
          })
        }
        // 500 服务器错误
        else if (res.statusCode >= 500) {
          reject({
            error: '服务器错误，请稍后重试',
            code: res.statusCode
          })
        }
        // 其他错误
        else {
          reject({
            error: res.data.error || res.data.message || '请求失败',
            code: res.statusCode,
            data: res.data
          })
        }
      },
      fail: (err) => {
        console.error('[wx.request fail] 错误:', err)
        console.error('网络请求失败:', err)

        // 判断错误类型
        let errorMsg = '网络请求失败'

        if (err.errMsg.includes('timeout')) {
          errorMsg = '请求超时，请检查网络连接'
        } else if (err.errMsg.includes('fail')) {
          errorMsg = '网络连接失败，请检查网络'
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
 * GET请求
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
 * POST请求
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
 * PUT请求
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
 * DELETE请求
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

    // 添加Token
    if (token) {
      header['Authorization'] = `Bearer ${token}`
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
        if (res.statusCode === 200) {
          try {
            const data = JSON.parse(res.data)
            resolve(data)
          } catch (e) {
            reject({
              error: '解析响应数据失败'
            })
          }
        } else if (res.statusCode === 401) {
          clearAuthInfo()
          wx.reLaunch({
            url: '/pages/login/login'
          })
          reject({
            error: '登录已过期',
            code: 401
          })
        } else {
          reject({
            error: '上传失败',
            code: res.statusCode
          })
        }
      },
      fail: (err) => {
        console.error('上传文件失败:', err)
        reject({
          error: '上传失败，请检查网络连接'
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
            error: '下载失败',
            code: res.statusCode
          })
        }
      },
      fail: (err) => {
        console.error('下载文件失败:', err)
        reject({
          error: '下载失败，请检查网络连接'
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
