// pages/referral/referral.js
const { post, get } = require('../../utils/request.js')

Page({
  data: {
    // 二维码
    qrcodeUrl: '',
    referralCode: '',
    shareText: '',
    // 存钱罐
    balance: 0,
    totalEarnings: 0,
    referralCount: 0,
    progress: 0,
    localUnlocked: false,
    cashUnlocked: false,
    // 佣金明细
    commissionHistory: [],
    // 本地消费
    showConsumeModal: false,
    consumeAmount: '',
    consumeLoading: false,
    // 提现
    showWithdrawModal: false,
    withdrawAmount: '',
    withdrawLoading: false
  },

  onLoad() {
    this.loadPiggyBank()
  },

  onShow() {
    this.loadPiggyBank()
  },

  /**
   * 加载存钱罐数据
   */
  async loadPiggyBank() {
    try {
      const res = await get('/api/referral/piggy-bank')
      if (res.success) {
        const progress = Math.min((res.balance / 10) * 100, 100)

        // 处理佣金明细，格式化时间
        const commissionHistory = (res.commission_history || []).map(item => ({
          ...item,
          formattedTime: this.formatTime(item.created_at),
          refereeNickname: item.referee_nickname || '未知用户'
        }))

        this.setData({
          balance: res.balance.toFixed(2),
          totalEarnings: res.total_earnings.toFixed(2),
          referralCount: res.referral_count,
          progress: progress.toFixed(1),
          localUnlocked: res.local_consumption_unlocked,
          cashUnlocked: res.cash_withdrawal_unlocked,
          commissionHistory: commissionHistory
        })
      }
    } catch (e) {
      console.error('加载存钱罐失败:', e)
    }
  },

  /**
   * 格式化时间
   */
  formatTime(timeStr) {
    if (!timeStr) return ''
    const date = new Date(timeStr)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return '刚刚'
    if (diffMins < 60) return `${diffMins}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`

    // 超过7天显示具体日期
    const month = date.getMonth() + 1
    const day = date.getDate()
    return `${month}月${day}日`
  },

  /**
   * 加载二维码
   */
  async loadQrcode() {
    wx.showLoading({ title: '加载中...' })
    try {
      const res = await post('/api/referral/qrcode', {})
      if (res.success) {
        this.setData({
          qrcodeUrl: res.qrcode_url,
          referralCode: res.referral_code,
          shareText: res.share_text
        })
      } else {
        wx.showToast({ title: res.error || '加载失败', icon: 'none' })
      }
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  /**
   * 预览二维码
   */
  previewQrcode() {
    wx.previewImage({
      current: this.data.qrcodeUrl,
      urls: [this.data.qrcodeUrl]
    })
  },

  /**
   * 下载二维码
   */
  downloadQrcode() {
    const qrcodeUrl = this.data.qrcodeUrl
    if (!qrcodeUrl) {
      wx.showToast({ title: '请先加载二维码', icon: 'none' })
      return
    }

    console.log('开始保存二维码:', qrcodeUrl)
    wx.showLoading({ title: '保存中...' })

    // 先检查相册授权状态
    wx.getSetting({
      success: (settingRes) => {
        const hasWritePhotosAlbumAuth = settingRes.authSetting['scope.writePhotosAlbum']

        if (hasWritePhotosAlbumAuth === false) {
          // 用户明确拒绝过，需要引导到设置
          wx.hideLoading()
          wx.showModal({
            title: '需要相册权限',
            content: '您已拒绝相册访问权限，请前往设置开启后才能保存二维码',
            confirmText: '去设置',
            cancelText: '取消',
            success: (modalRes) => {
              if (modalRes.confirm) {
                wx.openSetting()
              }
            }
          })
          return
        }

        // 未授权或已授权，尝试下载并保存
        this._saveQrcodeToAlbum(qrcodeUrl)
      },
      fail: () => {
        // getSetting 失败，直接尝试保存
        this._saveQrcodeToAlbum(qrcodeUrl)
      }
    })
  },

  /**
   * 实际保存二维码到相册
   */
  _saveQrcodeToAlbum(url) {
    // 如果是相对路径，转换为完整 URL
    let downloadUrl = url
    const { API_BASE_URL } = require('../../utils/constants.js')
    if (url.startsWith('/static/')) {
      downloadUrl = API_BASE_URL + url
    }

    console.log('下载二维码 URL:', downloadUrl)

    wx.downloadFile({
      url: downloadUrl,
      success: (res) => {
        console.log('downloadFile 成功:', res.statusCode, res.tempFilePath)
        if (res.statusCode !== 200) {
          wx.showToast({ title: '图片下载失败', icon: 'none' })
          return
        }

        wx.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: () => {
            wx.showToast({ title: '已保存到相册', icon: 'success' })
          },
          fail: (err) => {
            console.error('saveImageToPhotosAlbum 失败:', err)
            // 检查是否是权限问题
            if (err.errMsg && err.errMsg.includes('auth')) {
              wx.showModal({
                title: '保存失败',
                content: '需要相册保存权限，请前往设置开启',
                confirmText: '去设置',
                success: (modalRes) => {
                  if (modalRes.confirm) {
                    wx.openSetting()
                  }
                }
              })
            } else {
              wx.showToast({ title: '保存失败，请长按图片保存', icon: 'none' })
            }
          }
        })
      },
      fail: (err) => {
        console.error('downloadFile 失败:', err)
        wx.showModal({
          title: '下载失败',
          content: `无法下载二维码图片\n错误：${err.errMsg || '未知错误'}\n\n提示：您可以长按二维码图片保存`,
          showCancel: false
        })
      },
      complete: () => {
        wx.hideLoading()
      }
    })
  },

  /**
   * 本地消费
   */
  goConsumeCash() {
    if (!this.data.localUnlocked) {
      wx.showToast({ title: '余额不足10元，无法使用', icon: 'none' })
      return
    }
    this.setData({ showConsumeModal: true, consumeAmount: '' })
  },

  closeConsumeModal() {
    this.setData({ showConsumeModal: false })
  },

  onConsumeInput(e) {
    this.setData({ consumeAmount: e.detail.value })
  },

  async confirmConsume() {
    const amount = parseFloat(this.data.consumeAmount)
    if (!amount || amount <= 0) {
      wx.showToast({ title: '请输入有效金额', icon: 'none' })
      return
    }

    this.setData({ consumeLoading: true })
    try {
      const res = await post('/api/referral/consume-cash', { amount })
      if (res.success) {
        wx.showToast({ title: `购买成功，获得${res.hairs_received}发丝`, icon: 'success' })
        this.setData({ showConsumeModal: false, consumeAmount: '' })
        this.loadPiggyBank()
      } else {
        wx.showToast({ title: res.error || '消费失败', icon: 'none' })
      }
    } catch (e) {
      wx.showToast({ title: '消费失败', icon: 'none' })
    } finally {
      this.setData({ consumeLoading: false })
    }
  },

  /**
   * 提现
   */
  goWithdraw() {
    if (!this.data.cashUnlocked) {
      wx.showToast({ title: '余额不足10元，无法提现', icon: 'none' })
      return
    }
    this.setData({ showWithdrawModal: true, withdrawAmount: '' })
  },

  closeWithdrawModal() {
    this.setData({ showWithdrawModal: false })
  },

  onWithdrawInput(e) {
    this.setData({ withdrawAmount: e.detail.value })
  },

  async confirmWithdraw() {
    const amount = parseFloat(this.data.withdrawAmount)
    if (!amount || amount < 1) {
      wx.showToast({ title: '最低提现金额为1元', icon: 'none' })
      return
    }

    this.setData({ withdrawLoading: true })
    wx.showLoading({ title: '提现中...' })
    try {
      const res = await post('/api/referral/withdraw', { amount })
      wx.hideLoading()
      if (res.success) {
        wx.showToast({ title: '提现成功', icon: 'success' })
        this.setData({ showWithdrawModal: false, withdrawAmount: '' })
        this.loadPiggyBank()
      } else {
        wx.showToast({ title: res.error || '提现失败', icon: 'none' })
      }
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '提现失败', icon: 'none' })
    } finally {
      this.setData({ withdrawLoading: false })
    }
  },

  stopPropagation() {
    // 阻止事件冒泡
  },

  /**
   * 分享给好友
   */
  onShareAppMessage() {
    return {
      title: '快来试试发型迁移AI，一键换发型！',
      path: `/pages/index/index`
    }
  }
})
