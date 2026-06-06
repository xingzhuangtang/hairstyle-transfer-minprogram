// pages/chat/chat.js
import { sendChatMessage, getChatMessages, getUnreadCount } from '../../api/chat.js'
import { API_BASE_URL } from '../../utils/constants.js'
import { getToken } from '../../utils/storage.js'

const POLL_INTERVAL = 5000 // 5秒轮询
const MAX_RETRY = 3 // 连续失败最大重试次数

Page({
  data: {
    messages: [],
    inputValue: '',
    scrollToView: '',
    loading: false,
    lastMessageTime: null // 最后一条消息的时间戳，用于增量轮询
  },

  _pollTimer: null,
  _failCount: 0, // 连续失败次数
  _isPolling: false,

  onLoad() {
    this.loadHistory()
  },

  onShow() {
    this.startPolling()
    this.refreshBadge()
  },

  onHide() {
    this.stopPolling()
    this.markRead()
  },

  onUnload() {
    this.stopPolling()
    this.markRead()
  },

  /**
   * 加载历史消息
   */
  async loadHistory() {
    if (this.data.loading) return

    this.setData({ loading: true })

    try {
      const data = await getChatMessages(null, 50)
      const messages = (data.messages || []).map(msg => ({
        ...msg,
        timeText: this.formatTime(msg.created_at),
        status: msg.sender_type === 'user' ? 'sent' : null
      }))

      this.setData({
        messages,
        lastMessageTime: messages.length > 0 ? messages[messages.length - 1].created_at : null
      })

      // 滚动到底部
      if (messages.length > 0) {
        this.scrollToBottom()
      }
    } catch (e) {
      console.error('加载历史消息失败:', e)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 开始轮询
   */
  startPolling() {
    if (this._isPolling) return
    this._isPolling = true
    this._failCount = 0

    this._pollTimer = setInterval(() => {
      this.pollNewMessages()
    }, POLL_INTERVAL)

    // 立即执行一次
    this.pollNewMessages()
  },

  /**
   * 停止轮询
   */
  stopPolling() {
    this._isPolling = false
    if (this._pollTimer) {
      clearInterval(this._pollTimer)
      this._pollTimer = null
    }
  },

  /**
   * 轮询新消息
   */
  async pollNewMessages() {
    try {
      const data = await getChatMessages(this.data.lastMessageTime, 50)
      const newMessages = (data.messages || []).map(msg => ({
        ...msg,
        timeText: this.formatTime(msg.created_at),
        status: msg.sender_type === 'user' ? 'sent' : null
      }))

      if (newMessages.length > 0) {
        // 过滤掉已有的消息
        const existingIds = new Set(this.data.messages.map(m => m.id))
        const uniqueNewMessages = newMessages.filter(m => !existingIds.has(m.id))

        if (uniqueNewMessages.length > 0) {
          const updatedMessages = [...this.data.messages, ...uniqueNewMessages]
          const lastMsg = updatedMessages[updatedMessages.length - 1]

          this.setData({
            messages: updatedMessages,
            lastMessageTime: lastMsg.created_at
          })

          // 滚动到底部
          this.scrollToBottom()
        }
      }

      this._failCount = 0 // 重置失败计数
    } catch (e) {
      console.error('轮询失败:', e)
      this._failCount++

      // 连续失败3次后暂停轮询
      if (this._failCount >= MAX_RETRY) {
        this.stopPolling()
        console.log('轮询已暂停，请检查网络连接')
      }
    }
  },

  /**
   * 输入内容变化
   */
  onInputChange(e) {
    this.setData({
      inputValue: e.detail.value
    })
  },

  /**
   * 发送消息
   */
  async onSendMessage() {
    const content = this.data.inputValue.trim()
    if (!content) return

    // 乐观更新：先显示消息
    const tempId = Date.now()
    const tempMessage = {
      id: tempId,
      sender_type: 'user',
      content,
      timeText: this.formatTime(new Date().toISOString()),
      status: 'sending'
    }

    this.setData({
      inputValue: '',
      messages: [...this.data.messages, tempMessage]
    })
    this.scrollToBottom()

    try {
      const res = await sendChatMessage(content)

      // 更新为真实ID和状态
      const updatedMessages = this.data.messages.map(msg =>
        msg.id === tempId
          ? { ...msg, id: res.message.id, status: 'sent' }
          : msg
      )

      this.setData({ messages: updatedMessages })
      this.scrollToBottom()
    } catch (e) {
      console.error('发送失败:', e)

      // 标记为发送失败
      const updatedMessages = this.data.messages.map(msg =>
        msg.id === tempId ? { ...msg, status: 'failed' } : msg
      )

      this.setData({ messages: updatedMessages })
      wx.showToast({ title: e.message || '发送失败', icon: 'none' })
    }
  },

  /**
   * 重新发送失败的消息
   */
  onRetrySend(e) {
    const index = e.currentTarget.dataset.index
    const message = this.data.messages[index]

    if (!message || message.sender_type !== 'user') return

    // 临时设置inputValue为重发消息内容
    this.setData({ inputValue: message.content })
    this.onSendMessage()
  },

  /**
   * 滚动到底部
   */
  scrollToBottom() {
    const messages = this.data.messages
    if (messages.length > 0) {
      this.setData({
        scrollToView: `msg-${messages[messages.length - 1].id}`
      })
    }
  },

  /**
   * 格式化时间
   */
  formatTime(isoString) {
    if (!isoString) return ''
    const date = new Date(isoString.replace('Z', '+00:00'))
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  },

  /**
   * 标记所有未读消息为已读
   */
  async markRead() {
    try {
      wx.request({
        url: `${API_BASE_URL}/api/chat/mark-read`,
        method: 'POST',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`
        },
        success: (res) => {
          if (res.statusCode === 200 && res.data.success) {
            this.setData({ chatUnreadCount: 0 })
          }
        }
      })
    } catch (e) {
      console.error('标记已读失败:', e)
    }
  },

  /**
   * 刷新未读角标（返回 profile 页面时恢复显示）
   */
  async refreshBadge() {
    try {
      const count = await getUnreadCount()
      this.setData({ chatUnreadCount: count || 0 })
    } catch (e) {
      // 静默失败
    }
  }
})
