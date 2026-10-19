// pages/referral/referral.js
const { post, get } = require('../../utils/request.js')
const { onLocaleChange } = require('../../utils/i18n.js')

const app = getApp()

Page({
  data: {
    qrcodeUrl: '',
    qrcodeProxyUrl: '',
    qrcodeLocalPath: '',
    referralCode: '',
    shareText: '',
    balance: 0,
    totalEarnings: 0,
    referralCount: 0,
    progress: 0,
    localUnlocked: false,
    cashUnlocked: false,
    commissionHistory: [],
    showConsumeModal: false,
    consumeAmount: '',
    consumeLoading: false,
    showWithdrawModal: false,
    withdrawAmount: '',
    withdrawLoading: false,
    // i18n
    // i18n - WXML UI
    tReferralTitle: '我的惊喜',
    tCommonCancel: '取消',
    tReferralTipText: '甩出二维码，朋友注册账户成功，24小时以后，每使用两次素描效果功能，就能封顶99次迎娶人民币回家！',
    tReferralQrcodeCardTitle: '营销二维码',
    tReferralLoadQrcodeHint: '点击加载推广二维码',
    tReferralSaveQrcode: '保存二维码',
    tReferralShareToFriend: '分享给好友',
    tReferralLongPressTip: '长按图片也可保存到相册',
    tReferralPiggyBank: '存钱罐',
    tReferralTotalEarnings: '累计收益：',
    tReferralRefCount: '推广人数：',
    tReferralPeople: '人',
    tReferralLocalConsumption: '本地消费',
    tReferralAvailable: '可用',
    tReferralLocked: '未解锁',
    tReferralUseBalanceDesc: '用余额购买发丝',
    tReferralCashWithdraw: '提成现金',
    tReferralWithdrawDesc: '提现到微信零钱',
    tReferralCommissionDetail: '佣金明细',
    tReferralEmptyCommission: '暂无佣金记录',
    tReferralEmptyCommissionHint: '朋友使用素描效果后将在此显示佣金明细',
    tReferralConsumeModalTitle: '购买发丝',
    tReferralConsumeAmountLabel: '消费金额（元）',
    tReferralConsumePlaceholder: '请输入金额',
    tReferralExchangeRate: '兑换比例：1元 = 100发丝',
    tReferralConfirmPurchase: '确认购买',
    tReferralWithdrawModalTitle: '提现到微信零钱',
    tReferralWithdrawAmountLabel: '提现金额（元）',
    tReferralWithdrawPlaceholder: '请输入金额（最低1元）',
    tReferralWithdrawInfo: '提现将到账您的微信零钱，预计即时到账',
    tReferralConfirmWithdraw: '确认提现',
    tReferralUnknownUser: '未知用户',
    tReferralJustNow: '刚刚',
    tReferralMinutesAgo: '{mins}分钟前',
    tReferralHoursAgo: '{hours}小时前',
    tReferralDaysAgo: '{days}天前',
    tReferralDateFormat: '{month}月{day}日',
    tReferralLoading: '加载中...',
    tReferralLoadFail: '加载失败',
    tReferralLoadQrcodeFirst: '请先加载二维码',
    tReferralSaving: '保存中...',
    tReferralNeedAlbumPermission: '需要相册权限',
    tReferralAlbumPermissionContent: '请前往设置允许微信访问相册',
    tReferralGoToSettings: '去设置',
    tReferralSaveSuccess: '保存成功',
    tReferralSavedToAlbum: '二维码已保存到相册',
    tReferralSaveFail: '保存失败',
    tReferralSaveFailContent: '请长按图片选择"保存图片"',
    tReferralImageLoadFail: '图片加载失败',
    tReferralBalanceNotEnough: '余额不足10元，无法使用',
    tReferralEnterValidAmount: '请输入有效金额',
    tReferralConsumeSuccess: '购买成功，获得{hairs}发丝',
    tReferralConsumeFail: '消费失败',
    tReferralCashNotEnough: '余额不足10元，无法提现',
    tReferralMinWithdraw: '最低提现金额为1元',
    tReferralWithdrawing: '提现中...',
    tReferralWithdrawSuccess: '提现成功',
    tReferralWithdrawFail: '提现失败',
    tReferralShareTitle: '快来试试发型迁移AI，一键换发型！'
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'referral.title')
    this.loadPiggyBank()
  },

  onShow() {
    this._loadI18n()
    app.setNavTitle(this, 'referral.title')
    this.loadPiggyBank()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'referral.title')
    })
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      // i18n - WXML UI
      tReferralTitle: t('referral.title'),
      tCommonCancel: t('common.cancel'),
      tReferralTipText: t('referral.tipText'),
      tReferralQrcodeCardTitle: t('referral.qrcodeCardTitle'),
      tReferralLoadQrcodeHint: t('referral.loadQrcodeHint'),
      tReferralSaveQrcode: t('referral.saveQrcode'),
      tReferralShareToFriend: t('referral.shareToFriend'),
      tReferralLongPressTip: t('referral.longPressTip'),
      tReferralPiggyBank: t('referral.piggyBank'),
      tReferralTotalEarnings: t('referral.totalEarnings'),
      tReferralRefCount: t('referral.refCount'),
      tReferralPeople: t('referral.people'),
      tReferralLocalConsumption: t('referral.localConsumption'),
      tReferralAvailable: t('referral.available'),
      tReferralLocked: t('referral.locked'),
      tReferralUseBalanceDesc: t('referral.useBalanceDesc'),
      tReferralCashWithdraw: t('referral.cashWithdraw'),
      tReferralWithdrawDesc: t('referral.withdrawDesc'),
      tReferralCommissionDetail: t('referral.commissionDetail'),
      tReferralEmptyCommission: t('referral.emptyCommission'),
      tReferralEmptyCommissionHint: t('referral.emptyCommissionHint'),
      tReferralConsumeModalTitle: t('referral.consumeModalTitle'),
      tReferralConsumeAmountLabel: t('referral.consumeAmountLabel'),
      tReferralConsumePlaceholder: t('referral.consumePlaceholder'),
      tReferralExchangeRate: t('referral.exchangeRate'),
      tReferralConfirmPurchase: t('referral.confirmPurchase'),
      tReferralWithdrawModalTitle: t('referral.withdrawModalTitle'),
      tReferralWithdrawAmountLabel: t('referral.withdrawAmountLabel'),
      tReferralWithdrawPlaceholder: t('referral.withdrawPlaceholder'),
      tReferralWithdrawInfo: t('referral.withdrawInfo'),
      tReferralConfirmWithdraw: t('referral.confirmWithdraw'),
      tReferralUnknownUser: t('referral.unknownUser'),
      tReferralJustNow: t('referral.justNow'),
      tReferralMinutesAgo: t('referral.minutesAgo'),
      tReferralHoursAgo: t('referral.hoursAgo'),
      tReferralDaysAgo: t('referral.daysAgo'),
      tReferralDateFormat: t('referral.dateFormat'),
      tReferralLoading: t('referral.loading'),
      tReferralLoadFail: t('referral.loadFail'),
      tReferralLoadQrcodeFirst: t('referral.loadQrcodeFirst'),
      tReferralSaving: t('referral.saving'),
      tReferralNeedAlbumPermission: t('referral.needAlbumPermission'),
      tReferralAlbumPermissionContent: t('referral.albumPermissionContent'),
      tReferralGoToSettings: t('referral.goToSettings'),
      tReferralSaveSuccess: t('referral.saveSuccess'),
      tReferralSavedToAlbum: t('referral.savedToAlbum'),
      tReferralSaveFail: t('referral.saveFail'),
      tReferralSaveFailContent: t('referral.saveFailContent'),
      tReferralImageLoadFail: t('referral.imageLoadFail'),
      tReferralBalanceNotEnough: t('referral.balanceNotEnough'),
      tReferralEnterValidAmount: t('referral.enterValidAmount'),
      tReferralConsumeSuccess: t('referral.consumeSuccess'),
      tReferralConsumeFail: t('referral.consumeFail'),
      tReferralCashNotEnough: t('referral.cashNotEnough'),
      tReferralMinWithdraw: t('referral.minWithdraw'),
      tReferralWithdrawing: t('referral.withdrawing'),
      tReferralWithdrawSuccess: t('referral.withdrawSuccess'),
      tReferralWithdrawFail: t('referral.withdrawFail'),
      tReferralShareTitle: t('referral.shareTitle')
    })
  },

  async loadPiggyBank() {
    try {
      const res = await get('/api/referral/piggy-bank')
      if (res.success) {
        const progress = Math.min((res.balance / 10) * 100, 100)

        const commissionHistory = (res.commission_history || []).map(item => ({
          ...item,
          formattedTime: this.formatTime(item.created_at),
          refereeNickname: item.referee_nickname || this.data.tReferralUnknownUser
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

  formatTime(timeStr) {
    if (!timeStr) return ''
    const date = new Date(timeStr)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return this.data.tReferralJustNow
    if (diffMins < 60) return this.data.tReferralMinutesAgo.replace('{mins}', String(diffMins))
    if (diffHours < 24) return this.data.tReferralHoursAgo.replace('{hours}', String(diffHours))
    if (diffDays < 7) return this.data.tReferralDaysAgo.replace('{days}', String(diffDays))

    const month = date.getMonth() + 1
    const day = date.getDate()
    return this.data.tReferralDateFormat.replace('{month}', String(month)).replace('{day}', String(day))
  },

  async loadQrcode() {
    wx.showLoading({ title: this.data.tReferralLoading })
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
        wx.showToast({ title: res.error || this.data.tReferralLoadFail, icon: 'none' })
      }
    } catch (e) {
      wx.showToast({ title: this.data.tReferralLoadFail, icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  _downloadQrcodeToLocal() {
    const token = wx.getStorageSync('token') || ''
    const imageUrl = this.data.qrcodeProxyUrl

    wx.downloadFile({
      url: imageUrl,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200 && res.tempFilePath) {
          this.setData({ qrcodeLocalPath: res.tempFilePath })
        }
      },
      fail: (err) => {
        console.error('[loadQrcode] 下载图片失败:', err)
      }
    })
  },

  previewQrcode() {
    const url = this.data.qrcodeLocalPath || this.data.qrcodeProxyUrl || this.data.qrcodeUrl
    wx.previewImage({
      current: url,
      urls: [url]
    })
  },

  downloadQrcode() {
    if (!this.data.qrcodeUrl) {
      wx.showToast({ title: this.data.tReferralLoadQrcodeFirst, icon: 'none' })
      return
    }

    wx.showLoading({ title: this.data.tReferralSaving })

    wx.getSetting({
      success: (res) => {
        const auth = res.authSetting['scope.writePhotosAlbum']
        if (auth === false) {
          wx.hideLoading()
          wx.showModal({
            title: this.data.tReferralNeedAlbumPermission,
            content: this.data.tReferralAlbumPermissionContent,
            confirmText: this.data.tReferralGoToSettings,
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

  _saveToAlbum() {
    const saveFile = (filePath) => {
      wx.saveImageToPhotosAlbum({
        filePath: filePath,
        success: () => {
          wx.hideLoading()
          wx.showModal({
            title: this.data.tReferralSaveSuccess,
            content: this.data.tReferralSavedToAlbum,
            showCancel: false
          })
        },
        fail: (err) => {
          console.error('保存到相册失败:', err)
          wx.hideLoading()
          wx.showModal({
            title: this.data.tReferralSaveFail,
            content: this.data.tReferralSaveFailContent,
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
          wx.showToast({ title: this.data.tReferralImageLoadFail, icon: 'none' })
          return
        }
        saveFile(tempFilePath)
      })
    }
  },

  downloadQrcodeImage(callback) {
    const token = wx.getStorageSync('token') || ''
    const imageUrl = this.data.qrcodeProxyUrl || this.data.qrcodeUrl

    wx.downloadFile({
      url: imageUrl,
      header: { 'Authorization': `Bearer ${token}` },
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

  goConsumeCash() {
    if (!this.data.localUnlocked) {
      wx.showToast({ title: this.data.tReferralBalanceNotEnough, icon: 'none' })
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
      wx.showToast({ title: this.data.tReferralEnterValidAmount, icon: 'none' })
      return
    }

    this.setData({ consumeLoading: true })
    try {
      const res = await post('/api/referral/consume-cash', { amount })
      if (res.success) {
        wx.showToast({
          title: this.data.tReferralConsumeSuccess.replace('{hairs}', String(res.hairs_received)),
          icon: 'success'
        })
        this.setData({ showConsumeModal: false, consumeAmount: '' })
        this.loadPiggyBank()
      } else {
        wx.showToast({ title: res.error || this.data.tReferralConsumeFail, icon: 'none' })
      }
    } catch (e) {
      wx.showToast({ title: this.data.tReferralConsumeFail, icon: 'none' })
    } finally {
      this.setData({ consumeLoading: false })
    }
  },

  goWithdraw() {
    if (!this.data.cashUnlocked) {
      wx.showToast({ title: this.data.tReferralCashNotEnough, icon: 'none' })
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
      wx.showToast({ title: this.data.tReferralMinWithdraw, icon: 'none' })
      return
    }

    this.setData({ withdrawLoading: true })
    wx.showLoading({ title: this.data.tReferralWithdrawing })
    try {
      const res = await post('/api/referral/withdraw', { amount })
      wx.hideLoading()
      if (res.success) {
        wx.showToast({ title: this.data.tReferralWithdrawSuccess, icon: 'success' })
        this.setData({ showWithdrawModal: false, withdrawAmount: '' })
        this.loadPiggyBank()
      } else {
        wx.showToast({ title: res.error || this.data.tReferralWithdrawFail, icon: 'none' })
      }
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: this.data.tReferralWithdrawFail, icon: 'none' })
    } finally {
      this.setData({ withdrawLoading: false })
    }
  },

  stopPropagation() {},

  onShareAppMessage() {
    return {
      title: this.data.tReferralShareTitle,
      path: `/pages/index/index`
    }
  }
})
