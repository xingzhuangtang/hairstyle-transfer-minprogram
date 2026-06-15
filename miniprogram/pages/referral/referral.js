// pages/referral/referral.js
const { post, get } = require('../../utils/request.js')

Page({
  data: {
    // 二维码
    qrcodeUrl: '',
    qrcodeProxyUrl: '',
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
   * 保存二维码到相册
   */
  downloadQrcode() {
    const qrcodeUrl = this.data.qrcodeUrl
    if (!qrcodeUrl) {
      wx.showToast({ title: '请先加载二维码', icon: 'none' })
      return
    }

    wx.showLoading({ title: '保存中...' })

    // 先检查相册权限
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
        this._saveToAlbum(qrcodeUrl)
      },
      fail: () => {
        this._saveToAlbum(qrcodeUrl)
      }
    })
  },

  /**
   * 下载图片到本地临时文件（带认证头）
   */
  downloadQrcodeImage(callback) {
    const app = getApp()
    const token = app.globalData.token || wx.getStorageSync('token')
    const imageUrl = this.data.qrcodeProxyUrl || this.data.qrcodeUrl

    wx.downloadFile({
      url: imageUrl,
      header: {
        'Authorization': `Bearer ${token}`
      },
      success: (res) => {
        if (res.statusCode === 200 && res.tempFilePath) {
          callback(null, res.tempFilePath)
        } else {
          callback(new Error(`下载失败 statusCode=${res.statusCode}`))
        }
      },
      fail: (err) => {
        callback(err)
      }
    })
  },

  /**
   * 使用 canvas 绘制后保存到相册
   */
  _saveToAlbum(url) {
    this.downloadQrcodeImage((err, tempFilePath) => {
      if (err) {
        console.error('下载二维码图片失败:', err)
        wx.hideLoading()
        wx.showToast({ title: '图片加载失败', icon: 'none' })
        return
      }

      const ctx = wx.createCanvasContext('saveQrcodeCanvas', this)

      wx.getImageInfo({
        src: tempFilePath,
        success: (res) => {
          const width = res.width
          const height = res.height

          ctx.drawImage(res.path, 0, 0, width, height)
          ctx.draw(false, () => {
            setTimeout(() => {
              wx.canvasToTempFilePath({
                canvasId: 'saveQrcodeCanvas',
                x: 0,
                y: 0,
                width: width,
                height: height,
                destWidth: width,
                destHeight: height,
                fileType: 'png',
                success: (canvasRes) => {
                  console.log('canvas 生成成功:', canvasRes.tempFilePath)
                  this._saveImageToAlbum(canvasRes.tempFilePath)
                },
                fail: (err) => {
                  console.error('canvasToTempFilePath 失败:', err)
                  wx.hideLoading()
                  this._saveDirect(tempFilePath)
                }
              }, this)
            }, 100)
          })
        },
        fail: (err) => {
          console.error('getImageInfo 失败:', err)
          wx.hideLoading()
          wx.showToast({ title: '图片加载失败', icon: 'none' })
        }
      })
    })
  },

  /**
   * 备用方案：直接保存
   */
  _saveDirect(url) {
    this.downloadQrcodeImage((err, tempFilePath) => {
      if (err) {
        console.error('下载二维码图片失败:', err)
        wx.showToast({ title: '保存失败', icon: 'none' })
        return
      }

      wx.saveImageToPhotosAlbum({
        filePath: tempFilePath,
        success: () => {
          wx.showModal({
            title: '保存成功',
            content: '二维码已保存到相册',
            showCancel: false
          })
        },
        fail: () => {
          wx.showModal({
            title: '保存失败',
            content: '请长按图片选择"保存图片"',
            showCancel: false
          })
        }
      })
    })
  },

  /**
   * 保存图片到相册（处理权限）
   */
  _saveImageToAlbum(filePath) {
    wx.saveImageToPhotosAlbum({
      filePath: filePath,
      success: () => {
        wx.hideLoading()
        wx.showModal({
          title: '保存成功',
          content: '二维码已保存到相册\n\n请在相册中查找',
          showCancel: false
        })
      },
      fail: (err) => {
        console.error('保存到相册失败:', err)
        wx.hideLoading()
        if (err.errMsg && err.errMsg.includes('auth')) {
          wx.showModal({
            title: '需要相册权限',
            content: '请允许微信访问相册',
            confirmText: '去设置',
            success: (r) => { if (r.confirm) wx.openSetting() }
          })
        } else {
          wx.showModal({
            title: '保存失败',
            content: '请尝试长按图片保存',
            showCancel: false
          })
        }
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
