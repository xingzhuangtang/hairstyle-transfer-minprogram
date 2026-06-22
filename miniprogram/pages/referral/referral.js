// pages/referral/referral.js
const { post, get } = require('../../utils/request.js')
const { onLocaleChange } = require('../../utils/i18n.js')

const app = getApp()

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
    withdrawLoading: false,
    // i18n
    tReferralTitle: '',
    tReferralTipText: '',
    tReferralQrcodeCardTitle: '',
    tReferralLoadQrcodeHint: '',
    tReferralSaveQrcode: '',
    tReferralShareToFriend: '',
    tReferralPiggyBank: '',
    tReferralTotalEarnings: '',
    tReferralReferralCount: '',
    tReferralLocalConsumption: '',
    tReferralUnlocked: '',
    tReferralLocked: '',
    tReferralUseBalanceDesc: '',
    tReferralCashWithdraw: '',
    tReferralWithdrawDesc: '',
    tReferralCommissionDetail: '',
    tReferralEmptyCommission: '',
    tReferralEmptyCommissionHint: '',
    tReferralConsumeModalTitle: '',
    tReferralConsumeAmountLabel: '',
    tReferralConsumeAmountPlaceholder: '',
    tReferralExchangeRate: '',
    tReferralConfirmPurchase: '',
    tReferralWithdrawModalTitle: '',
    tReferralWithdrawAmountLabel: '',
    tReferralWithdrawAmountPlaceholder: '',
    tReferralWithdrawInfo: '',
    tReferralConfirmWithdraw: '',
    tReferralBalanceNotEnough: '',
    tReferralCashNotEnough: '',
    tReferralInvalidAmount: '',
    tReferralMinWithdrawAmount: '',
    tReferralConsumeSuccess: '',
    tReferralConsumeFail: '',
    tReferralWithdrawSuccess: '',
    tReferralWithdrawFail: '',
    tReferralShareTitle: '',
    tReferralPeople: '',
    tReferralYuan: '',
    tCommonCancel: ''
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    this.loadPiggyBank()
  },

  onShow() {
    this._loadI18n()
    this.loadPiggyBank()
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tReferralTitle: t('referral.title'),
      tReferralTipText: t('referral.tipText'),
      tReferralQrcodeCardTitle: t('referral.qrcodeCardTitle'),
      tReferralLoadQrcodeHint: t('referral.loadQrcodeHint'),
      tReferralSaveQrcode: t('referral.saveQrcode'),
      tReferralShareToFriend: t('referral.shareToFriend'),
      tReferralPiggyBank: t('referral.piggyBank'),
      tReferralTotalEarnings: t('referral.totalEarnings') + '：' + t('referral.yuan'),
      tReferralReferralCount: t('referral.referralCount') + '：',
      tReferralLocalConsumption: t('referral.localConsumption'),
      tReferralUnlocked: t('referral.unlocked'),
      tReferralLocked: t('referral.locked'),
      tReferralUseBalanceDesc: t('referral.useBalanceDesc'),
      tReferralCashWithdraw: t('referral.cashWithdraw'),
      tReferralWithdrawDesc: t('referral.withdrawDesc'),
      tReferralCommissionDetail: t('referral.commissionDetail'),
      tReferralEmptyCommission: t('referral.emptyCommission'),
      tReferralEmptyCommissionHint: t('referral.emptyCommissionHint'),
      tReferralConsumeModalTitle: t('referral.consumeModalTitle'),
      tReferralConsumeAmountLabel: t('referral.consumeAmountLabel'),
      tReferralConsumeAmountPlaceholder: t('referral.consumeAmountPlaceholder'),
      tReferralExchangeRate: t('referral.exchangeRate'),
      tReferralConfirmPurchase: t('referral.confirmPurchase'),
      tReferralWithdrawModalTitle: t('referral.withdrawModalTitle'),
      tReferralWithdrawAmountLabel: t('referral.withdrawAmountLabel'),
      tReferralWithdrawAmountPlaceholder: t('referral.withdrawAmountPlaceholder'),
      tReferralWithdrawInfo: t('referral.withdrawInfo'),
      tReferralConfirmWithdraw: t('referral.confirmWithdraw'),
      tReferralBalanceNotEnough: t('referral.balanceNotEnough'),
      tReferralCashNotEnough: t('referral.cashNotEnough'),
      tReferralInvalidAmount: t('referral.invalidAmount'),
      tReferralMinWithdrawAmount: t('referral.minWithdrawAmount'),
      tReferralConsumeSuccess: t('referral.consumeSuccess'),
      tReferralConsumeFail: t('referral.consumeFail'),
      tReferralWithdrawSuccess: t('referral.withdrawSuccess'),
      tReferralWithdrawFail: t('referral.withdrawFail'),
      tReferralShareTitle: t('referral.shareTitle'),
      tReferralPeople: t('referral.people'),
      tReferralYuan: t('referral.yuan'),
      tCommonCancel: t('common.cancel'),
      tCommonLoading: t('common.loading'),
      tCommonLoadFail: t('common.loadFail'),
      tReferralSaving: t('referral.saving'),
      tReferralSaveSuccess: t('referral.savedToAlbum'),
      tReferralSaveFail: t('common.uploadFail'),
      tDownloadFail: t('common.downloadFailNetwork'),
      tWithdrawing: t('referral.withdrawing')
    })
    this._updateNavTitle()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
    })
  },

  _updateNavTitle() {
    app.setNavTitle(this, 'referral.title')
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
          refereeNickname: item.referee_nickname || t('common.unknown')
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
    wx.showLoading({ title: this.data.tCommonLoading })
    try {
      const res = await post('/api/referral/qrcode', {})
      if (res.success) {
        this.setData({
          qrcodeUrl: res.qrcode_url,
          referralCode: res.referral_code,
          shareText: res.share_text
        })
      } else {
        wx.showToast({ title: res.error || this.data.tCommonLoadFail, icon: 'none' })
      }
    } catch (e) {
      wx.showToast({ title: this.data.tCommonLoadFail, icon: 'none' })
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
    wx.showLoading({ title: this.data.tReferralSaving })
    wx.downloadFile({
      url: this.data.qrcodeUrl,
      success: (res) => {
        wx.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: () => {
            wx.showToast({ title: this.data.tReferralSaveSuccess, icon: 'success' })
          },
          fail: () => {
            wx.showToast({ title: this.data.tReferralSaveFail, icon: 'none' })
          }
        })
      },
      fail: () => {
        wx.showToast({ title: this.data.tDownloadFail, icon: 'none' })
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
      wx.showToast({ title: this.data.tReferralInvalidAmount, icon: 'none' })
      return
    }

    this.setData({ consumeLoading: true })
    try {
      const res = await post('/api/referral/consume-cash', { amount })
      if (res.success) {
        const msg = this.data.tReferralConsumeSuccess.replace('{hairs}', String(res.hairs_received))
        wx.showToast({ title: msg, icon: 'success' })
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

  /**
   * 提现
   */
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
      wx.showToast({ title: this.data.tReferralMinWithdrawAmount, icon: 'none' })
      return
    }

    this.setData({ withdrawLoading: true })
    wx.showLoading({ title: this.data.tWithdrawing })
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

  stopPropagation() {
    // 阻止事件冒泡
  },

  /**
   * 分享给好友
   */
  onShareAppMessage() {
    return {
      title: this.data.tReferralShareTitle,
      path: `/pages/index/index`
    }
  }
})
