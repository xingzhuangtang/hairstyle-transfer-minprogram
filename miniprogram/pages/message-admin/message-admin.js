// pages/message-admin/message-admin.js
import { API_BASE_URL } from '../../utils/constants.js'
import { getToken } from '../../utils/storage.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    messages: [],
    total: 0,
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    // i18n
    tMsgAdminTitle: '',
    tMsgAdminTotal: '',
    tMsgAdminEmpty: '',
    tMsgAdminLoadMore: '',
    tMsgAdminLoading: '',
    tMsgAdminLoadFail: '',
    tMsgAdminNetworkFail: '',
    tMsgAdminNoAccess: '',
    tMsgAdminPhoneCopied: '',
    tMsgAdminTotalTpl: ''
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'messageAdmin.title')
    this.loadMessages()
  },

  onShow() {
    this._loadI18n()
    app.setNavTitle(this, 'messageAdmin.title')
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tMsgAdminTitle: t('messageAdmin.title'),
      tMsgAdminTotal: '',
      tMsgAdminEmpty: t('messageAdmin.empty'),
      tMsgAdminLoadMore: t('history.loadMore'),
      tMsgAdminLoading: t('messageAdmin.loading'),
      tMsgAdminLoadFail: t('messageAdmin.loadFail'),
      tMsgAdminNetworkFail: t('message.networkFail'),
      tMsgAdminNoAccess: t('messageAdmin.noAccess'),
      tMsgAdminPhoneCopied: t('messageAdmin.phoneCopied'),
      tMsgAdminTotalTpl: t('messageAdmin.totalCount')
    })
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'messageAdmin.title')
    })
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
              reject(new Error(this.data.tMsgAdminNoAccess))
            } else {
              reject(new Error(res.data.error || this.data.tMsgAdminLoadFail))
            }
          },
          fail: (err) => {
            reject(new Error(this.data.tMsgAdminNetworkFail))
          }
        })
      }).then((data) => {
        const newMessages = data.messages || []
        const formattedMessages = newMessages.map(msg => {
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

        // 更新总数显示
        this.setData({
          tMsgAdminTotal: this.data.tMsgAdminTotalTpl.replace('{n}', String(this.data.total))
        })
      })

    } catch (e) {
      console.error('加载留言失败:', e)
      wx.showToast({
        title: e.message || this.data.tMsgAdminLoadFail,
        icon: 'none',
        duration: 2000
      })

      // 如果是权限错误，返回上一页
      if (e.message.includes(this.data.tMsgAdminNoAccess)) {
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
          title: this.data.tMsgAdminPhoneCopied,
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
