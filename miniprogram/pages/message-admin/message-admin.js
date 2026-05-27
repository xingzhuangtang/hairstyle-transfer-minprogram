// pages/message-admin/message-admin.js
import { API_BASE_URL } from '../../utils/constants.js'
import { getToken } from '../../utils/storage.js'

Page({
  data: {
    messages: [],
    total: 0,
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false
  },

  onLoad() {
    this.loadMessages()
  },

  /**
   * 加载留言列表
   */
  async loadMessages() {
    if (this.data.loading) return

    this.setData({ loading: true })

    try {
      const { page, pageSize } = this.data
      const token = getToken()

      await new Promise((resolve, reject) => {
        wx.request({
          url: `${API_BASE_URL}/api/messages`,
          method: 'GET',
          data: {
            page: page,
            page_size: pageSize
          },
          header: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          success: (res) => {
            if (res.statusCode === 200) {
              resolve(res.data)
            } else if (res.statusCode === 403) {
              reject(new Error('无权访问，仅开发者可查看'))
            } else {
              reject(new Error(res.data.error || '加载失败'))
            }
          },
          fail: (err) => {
            reject(new Error('网络请求失败'))
          }
        })
      }).then((data) => {
        const newMessages = data.messages || []
        const formattedMessages = newMessages.map(msg => {
          // 格式化时间
          const date = new Date(msg.created_at)
          const formattedTime = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
          return {
            ...msg,
            created_at: formattedTime
          }
        })

        this.setData({
          messages: page === 1 ? formattedMessages : [...this.data.messages, ...formattedMessages],
          total: data.total || 0,
          hasMore: (page * pageSize) < (data.total || 0)
        })
      })

    } catch (e) {
      console.error('加载留言失败:', e)
      wx.showToast({
        title: e.message || '加载失败',
        icon: 'none',
        duration: 2000
      })

      // 如果是权限错误，返回上一页
      if (e.message.includes('无权访问')) {
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      }
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 复制电话号码
   */
  copyPhone(e) {
    const phone = e.currentTarget.dataset.phone
    wx.setClipboardData({
      data: phone,
      success: () => {
        wx.showToast({
          title: '电话已复制',
          icon: 'success',
          duration: 1500
        })
      }
    })
  },

  /**
   * 加载更多
   */
  loadMore() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({
        page: this.data.page + 1
      })
      this.loadMessages()
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    this.setData({
      page: 1,
      messages: [],
      hasMore: true
    })
    this.loadMessages().then(() => {
      wx.stopPullDownRefresh()
    })
  }
})
