// api/chat.js
import { API_BASE_URL } from '../utils/constants.js'
import { getToken } from '../utils/storage.js'

/**
 * 发送聊天消息
 */
export function sendChatMessage(content) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}/api/chat/send`,
      method: 'POST',
      data: { content },
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.success) {
          resolve(res.data)
        } else {
          reject(new Error(res.data.error || getApp().t('chat.sendFail')))
        }
      },
      fail: reject
    })
  })
}

/**
 * 获取聊天消息
 */
export function getChatMessages(since = null, limit = 50) {
  return new Promise((resolve, reject) => {
    const params = { limit }
    if (since) params.since = since

    wx.request({
      url: `${API_BASE_URL}/api/chat/messages`,
      method: 'GET',
      data: params,
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.success) {
          resolve(res.data)
        } else {
          reject(new Error(res.data.error || getApp().t('chat.loadFail')))
        }
      },
      fail: reject
    })
  })
}

/**
 * 获取未读消息数
 */
export function getUnreadCount() {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}/api/chat/unread-count`,
      method: 'GET',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.success) {
          resolve(res.data.unread_count)
        } else {
          reject(new Error(res.data.error || getApp().t('chat.loadFail')))
        }
      },
      fail: reject
    })
  })
}
