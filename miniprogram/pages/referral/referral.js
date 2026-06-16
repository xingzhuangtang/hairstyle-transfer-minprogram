// pages/referral/referral.js
const { post, get } = require('../../utils/request.js')

Page({
  data: {
    // 二维码
    qrcodeUrl: '',
    qrcodeProxyUrl: '',
    qrcodeLocalPath: '',
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
        const { API_BASE_URL } = require('../../utils/constants.js')
        this.setData({
          qrcodeUrl: res.qrcode_url,
          qrcodeProxyUrl: `${API_BASE_URL}/api/referral/qrcode-image`,
          referralCode: res.referral_code,
          shareText: res.share_text
        })
        this._downloadQrcodeToLocal()
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
   * 下载二维码图片到本地临时文件（用于页面显示）
   */
  _downloadQrcodeToLocal() {
    const token = wx.getStorageSync('token') || ''
    const imageUrl = this.data.qrcodeProxyUrl

    wx.downloadFile({
      url: imageUrl,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200 && res.tempFilePath) {
          console.log('[loadQrcode] 图片已下载到本地:', res.tempFilePath)
          this.setData({ qrcodeLocalPath: res.tempFilePath })
        } else {
          console.error('[loadQrcode] 下载图片失败:', res.statusCode)
        }
      },
      fail: (err) => {
        console.error('[loadQrcode] 下载图片失败:', err)
      }
    })
  },

  /**
   * 预览二维码
   */
  previewQrcode() {
    const url = this.data.qrcodeLocalPath || this.data.qrcodeProxyUrl || this.data.qrcodeUrl
    wx.previewImage({
      current: url,
      urls: [url]
    })
  },

  /**
   * 保存二维码到相册
   */
  downloadQrcode() {
    if (!this.data.qrcodeUrl) {
      wx.showToast({ title: '请先加载二维码', icon: 'none' })
      return
    }

    wx.showLoading({ title: '保存中...' })

    wx.getSetting({
      success: (res) => {
        const auth = res.authSetting['scope.writePhotosAlbum']
        if (auth === false) {
          wx.hideLoading()
          wx.showModal({
            title: '需要相册权限',
            content: '请前往设置允许微信访问相册',
            confirmText: '去设置',
            success: (r) => { if (r.confirm) wx.openSetting() }
          })
          return
        }
        this._saveToAlbum()
      },
      fail: () => {
        this._saveToAlbum()
      }
    })
  },

  /**
   * 保存到相册（复用已下载的本地文件，或重新下载）
   */
  _saveToAlbum() {
    const saveFile = (filePath) => {
      wx.saveImageToPhotosAlbum({
        filePath: filePath,
        success: () => {
          wx.hideLoading()
          wx.showModal({
            title: '保存成功',
            content: '二维码已保存到相册',
            showCancel: false
          })
        },
        fail: (err) => {
          console.error('保存到相册失败:', err)
          wx.hideLoading()
          wx.showModal({
            title: '保存失败',
            content: '请长按图片选择"保存图片"',
            showCancel: false
          })
        }
      })
    }

    if (this.data.qrcodeLocalPath) {
      saveFile(this.data.qrcodeLocalPath)
    } else {
      this.downloadQrcodeImage((err, tempFilePath) => {
        if (err) {
          console.error('下载二维码图片失败:', err)
          wx.hideLoading()
          wx.showToast({ title: '图片加载失败', icon: 'none' })
          return
        }
        saveFile(tempFilePath)
      })
    }
  },

  /**
   * 下载图片到本地临时文件（带认证头）
   */
  downloadQrcodeImage(callback) {
    const token = wx.getStorageSync('token') || ''
    const imageUrl = this.data.qrcodeProxyUrl || this.data.qrcodeUrl

    console.log('[downloadQrcodeImage] url:', imageUrl, 'hasToken:', !!token)

    wx.downloadFile({
      url: imageUrl,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        console.log('[downloadQrcodeImage] statusCode:', res.statusCode, 'tempFilePath:', res.tempFilePath)
        if (res.statusCode === 200 && res.tempFilePath) {
          callback(null, res.tempFilePath)
        } else {
          callback(new Error(`下载失败 statusCode=${res.statusCode}`))
        }
      },
      fail: (err) => {
        console.error('[downloadQrcodeImage] fail:', err)
        callback(err)
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
