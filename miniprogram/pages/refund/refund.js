const { applyRefund } = require('../../api/refund.js')
const { getToken } = require('../../utils/storage.js')
const { onLocaleChange } = require('../../utils/i18n.js')

const app = getApp()

Page({
  data: {
    refundType: 'recharge',
    refundAmount: '',
    reason: '',
    suggestions: '',
    applicantName: '',
    applicantPhone: '',
    submitting: false,
    userInfo: null,
    // i18n
    tRefundRefundType: '',
    tRefundRechargeRefund: '',
    tRefundMembershipRefund: '',
    tRefundRefundAmount: '',
    tRefundAmountPlaceholder: '',
    tRefundMembershipAutoCalc: '',
    tRefundReasonLabel: '',
    tRefundReasonPlaceholder: '',
    tRefundSuggestionsLabel: '',
    tRefundSuggestionsPlaceholder: '',
    tRefundApplicantInfo: '',
    tRefundNameLabel: '',
    tRefundNamePlaceholder: '',
    tRefundPhoneLabel: '',
    tRefundPhonePlaceholder: '',
    tRefundSubmitBtn: '',
    tRefundSubmitting: '',
    tRefundSelectRefundType: '',
    tRefundEnterAmount: '',
    tRefundEnterReason: '',
    tRefundEnterName: '',
    tRefundEnterPhone: '',
    tRefundLoginFirst: '',
    tRefundSubmitSuccess: '',
    tRefundSubmitFail: '',
    tRefundNetworkError: ''
  },

  onLoad(options) {
    this._loadI18n()
    this._setupLocaleListener()
    // 获取用户信息
    const userInfo = wx.getStorageSync('user_info')
    if (userInfo) {
      this.setData({
        userInfo,
        applicantName: userInfo.nickname || '',
        applicantPhone: userInfo.phone || ''
      })
    }
  },

  onShow() {
    this._loadI18n()
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tRefundRefundType: t('refund.refundType'),
      tRefundRechargeRefund: t('refund.rechargeRefund'),
      tRefundMembershipRefund: t('refund.membershipRefund'),
      tRefundRefundAmount: t('refund.refundAmount'),
      tRefundAmountPlaceholder: t('refund.amountPlaceholder'),
      tRefundMembershipAutoCalc: t('refund.membershipAutoCalc'),
      tRefundReasonLabel: t('refund.reasonLabel'),
      tRefundReasonPlaceholder: t('refund.reasonPlaceholder'),
      tRefundSuggestionsLabel: t('refund.suggestionsLabel'),
      tRefundSuggestionsPlaceholder: t('refund.suggestionsPlaceholder'),
      tRefundApplicantInfo: t('refund.applicantInfo'),
      tRefundNameLabel: t('refund.nameLabel'),
      tRefundNamePlaceholder: t('refund.namePlaceholder'),
      tRefundPhoneLabel: t('refund.phoneLabel'),
      tRefundPhonePlaceholder: t('refund.phonePlaceholder'),
      tRefundSubmitBtn: t('refund.submitBtn'),
      tRefundSubmitting: t('refund.submitting'),
      tRefundSelectRefundType: t('refund.selectRefundType'),
      tRefundEnterAmount: t('refund.enterAmount'),
      tRefundEnterReason: t('refund.enterReason'),
      tRefundEnterName: t('refund.enterName'),
      tRefundEnterPhone: t('refund.enterPhone'),
      tRefundLoginFirst: t('refund.loginFirst'),
      tRefundSubmitSuccess: t('refund.submitSuccess'),
      tRefundSubmitFail: t('refund.submitFail'),
      tRefundNetworkError: t('refund.networkError')
    })
    this._updateNavTitle()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
    })
  },

  _updateNavTitle() {
    app.setNavTitle(this, 'refund.title')
  },

  onRefundTypeChange(e) {
    this.setData({
      refundType: e.detail.value,
      refundAmount: e.detail.value === 'membership' ? '' : this.data.refundAmount
    })
  },

  onAmountInput(e) {
    this.setData({ refundAmount: e.detail.value })
  },

  onReasonInput(e) {
    this.setData({ reason: e.detail.value })
  },

  onSuggestionsInput(e) {
    this.setData({ suggestions: e.detail.value })
  },

  onNameInput(e) {
    this.setData({ applicantName: e.detail.value })
  },

  onPhoneInput(e) {
    this.setData({ applicantPhone: e.detail.value })
  },

  onSubmit() {
    const { refundType, refundAmount, reason, suggestions, applicantName, applicantPhone, submitting } = this.data

    if (submitting) return

    // 验证
    if (!refundType) {
      wx.showToast({ title: this.data.tRefundSelectRefundType, icon: 'none' })
      return
    }

    if (!refundAmount || parseFloat(refundAmount) <= 0) {
      wx.showToast({ title: this.data.tRefundEnterAmount, icon: 'none' })
      return
    }

    if (!reason || reason.trim().length === 0) {
      wx.showToast({ title: this.data.tRefundEnterReason, icon: 'none' })
      return
    }

    if (!applicantName || applicantName.trim().length === 0) {
      wx.showToast({ title: this.data.tRefundEnterName, icon: 'none' })
      return
    }

    if (!applicantPhone || !/^1\d{10}$/.test(applicantPhone)) {
      wx.showToast({ title: this.data.tRefundEnterPhone, icon: 'none' })
      return
    }

    // 检查 token
    const token = getToken()
    if (!token) {
      wx.showToast({ title: this.data.tRefundLoginFirst, icon: 'none' })
      return
    }

    this.setData({ submitting: true })

    applyRefund({
      refund_type: refundType,
      refund_amount: parseFloat(refundAmount),
      reason: reason.trim(),
      applicant_name: applicantName.trim(),
      applicant_phone: applicantPhone.trim(),
      suggestions: suggestions.trim() || undefined
    }).then(res => {
      if (res.success) {
        wx.showToast({ title: this.data.tRefundSubmitSuccess, icon: 'success' })
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({ title: res.error || this.data.tRefundSubmitFail, icon: 'none' })
      }
    }).catch(err => {
      console.error('提交退款申请失败:', err)
      wx.showToast({ title: err.error || this.data.tRefundNetworkError, icon: 'none' })
    }).finally(() => {
      this.setData({ submitting: false })
    })
  }
})
