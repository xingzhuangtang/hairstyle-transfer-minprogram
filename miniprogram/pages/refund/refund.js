const { applyRefund } = require('../../api/refund.js')
const { getToken } = require('../../utils/storage.js')
const { API_BASE_URL } = require('../../utils/constants.js')
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
    calculation: null,
    calculating: false,
    showCalculation: false,
    rechargeOptions: [],
    rechargePickerRange: [],
    selectedOptionIndex: -1,
    loadingOptions: true,
    // i18n
    // i18n - WXML UI
    tRefundTypeLabel: '退款类型', tRefundRecharge: '充值退款', tRefundMembership: '会员退款',
    tRefundAmountLabel: '退款金额', tRefundLoadingOpts: '加载中...', tRefundNoRecords: '暂无充值记录',
    tRefundSelectRecord: '请选择要退款的充值记录',
    tRefundMembershipAuto: '会员退款将按剩余天数自动计算可退金额',
    tRefundMembershipPlaceholder: '会员退款自动计算',
    tRefundReasonLabel: '退款原因', tRefundReasonPlaceholder: '请详细说明退款原因',
    tRefundSuggestionsLabel: '对本项目的建议（选填）', tRefundSuggestionsPlaceholder: '您的建议对我们很重要',
    tRefundApplicantInfo: '申请人信息', tRefundNameLabel: '姓名', tRefundNamePlaceholder: '请输入姓名',
    tRefundPhoneLabel: '电话', tRefundPhonePlaceholder: '请输入手机号',
    tRefundCalcSection: '退款核算', tRefundCalcHint: '选择充值记录后，可先查看核算清单了解最终退款金额',
    tRefundCalcBtn: '查看退款核算清单', tRefundCalculating: '计算中...',
    tRefundCalcTitle: '退款核算清单', tRefundChargeAmount: '充值金额', tRefundChargeHairs: '获得发丝',
    tRefundHairsUnit: '根', tRefundApplyAmount: '申请退款', tRefundMemberPrice: '会员价格',
    tRefundRemainingDays: '剩余天数', tRefundAmountDue: '应退金额', tRefundDaysUnit: '天',
    tRefundDeductHairs: '应扣回发丝（剪刀卡槽）', tRefundCurrentScissor: '当前剪刀卡槽',
    tRefundCurrentComb: '当前梳子卡槽（赠送）', tRefundHairShortage: '发丝差额',
    tRefundCashDeduction: '现金抵扣', tRefundFinalRefund: '最终退款金额',
    tRefundSufficientTip: '剪刀发丝充足，全额退款',
    tRefundInsufficientTip: '剪刀发丝不足，差额按 0.01元/发丝 从退款中扣除',
    tRefundSubmitBtn: '提交退款申请', tRefundSubmitting: '提交中...',
    tRefundNotRefundable: '该笔充值不可退',
    tRefundSelectAmountFirst: '请先选择退款金额',
    tRefundLoginFirst: '请先登录',
    tRefundCalcFail: '计算失败',
    tRefundNetworkFail: '网络请求失败',
    tRefundCalcGenerated: '核算清单已生成',
    tRefundSelectTypeFirst: '请选择退款类型',
    tRefundSelectRecordFirst: '请选择要退款的充值记录',
    tRefundEnterReason: '请填写退款原因',
    tRefundEnterName: '请填写姓名',
    tRefundEnterPhone: '请填写正确的手机号',
    tRefundSubmitSuccess: '申请提交成功',
    tRefundSubmitFail: '提交失败',
    tRefundNetworkError: '网络错误，请稍后重试'
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'refund.title')
    const userInfo = wx.getStorageSync('user_info')
    if (userInfo) {
      this.setData({
        userInfo,
        applicantName: userInfo.nickname || '',
        applicantPhone: userInfo.phone || ''
      })
    }
    this.loadRechargeOptions()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'refund.title')
    })
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      // i18n - WXML UI
      tRefundTypeLabel: t('refund.typeLabel'),
      tRefundRecharge: t('refund.recharge'),
      tRefundMembership: t('refund.membership'),
      tRefundAmountLabel: t('refund.amountLabel'),
      tRefundLoadingOpts: t('refund.loadingOpts'),
      tRefundNoRecords: t('refund.noRecords'),
      tRefundSelectRecord: t('refund.selectRecord'),
      tRefundMembershipAuto: t('refund.membershipAuto'),
      tRefundMembershipPlaceholder: t('refund.membershipPlaceholder'),
      tRefundReasonLabel: t('refund.reasonLabel'),
      tRefundReasonPlaceholder: t('refund.reasonPlaceholder'),
      tRefundSuggestionsLabel: t('refund.suggestionsLabel'),
      tRefundSuggestionsPlaceholder: t('refund.suggestionsPlaceholder'),
      tRefundApplicantInfo: t('refund.applicantInfo'),
      tRefundNameLabel: t('refund.nameLabel'),
      tRefundNamePlaceholder: t('refund.namePlaceholder'),
      tRefundPhoneLabel: t('refund.phoneLabel'),
      tRefundPhonePlaceholder: t('refund.phonePlaceholder'),
      tRefundCalcSection: t('refund.calcSection'),
      tRefundCalcHint: t('refund.calcHint'),
      tRefundCalcBtn: t('refund.calcBtn'),
      tRefundCalculating: t('refund.calculating'),
      tRefundCalcTitle: t('refund.calcTitle'),
      tRefundChargeAmount: t('refund.chargeAmount'),
      tRefundChargeHairs: t('refund.chargeHairs'),
      tRefundHairsUnit: t('refund.hairsUnit'),
      tRefundApplyAmount: t('refund.applyAmount'),
      tRefundMemberPrice: t('refund.memberPrice'),
      tRefundRemainingDays: t('refund.remainingDays'),
      tRefundAmountDue: t('refund.amountDue'),
      tRefundDaysUnit: t('refund.daysUnit'),
      tRefundDeductHairs: t('refund.deductHairs'),
      tRefundCurrentScissor: t('refund.currentScissor'),
      tRefundCurrentComb: t('refund.currentComb'),
      tRefundHairShortage: t('refund.hairShortage'),
      tRefundCashDeduction: t('refund.cashDeduction'),
      tRefundFinalRefund: t('refund.finalRefund'),
      tRefundSufficientTip: t('refund.sufficientTip'),
      tRefundInsufficientTip: t('refund.insufficientTip'),
      tRefundSubmitBtn: t('refund.submitBtn'),
      tRefundSubmitting: t('refund.submitting'),
      tRefundNotRefundable: t('refund.notRefundable'),
      tRefundSelectAmountFirst: t('refund.selectAmountFirst'),
      tRefundLoginFirst: t('refund.loginFirst'),
      tRefundCalcFail: t('refund.calcFail'),
      tRefundNetworkFail: t('refund.networkFail'),
      tRefundCalcGenerated: t('refund.calcGenerated'),
      tRefundSelectTypeFirst: t('refund.selectTypeFirst'),
      tRefundSelectRecordFirst: t('refund.selectRecordFirst'),
      tRefundEnterReason: t('refund.enterReason'),
      tRefundEnterName: t('refund.enterName'),
      tRefundEnterPhone: t('refund.enterPhone'),
      tRefundSubmitSuccess: t('refund.submitSuccess'),
      tRefundSubmitFail: t('refund.submitFail'),
      tRefundNetworkError: t('refund.networkError')
    })
  },

  loadRechargeOptions() {
    const token = getToken()
    if (!token) {
      this.setData({ loadingOptions: false })
      return
    }

    wx.request({
      url: `${API_BASE_URL}/api/refund/recharge-options`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.success) {
          const options = res.data.options
          const range = options.map(opt => opt.display)
          this.setData({
            rechargeOptions: options,
            rechargePickerRange: range,
            loadingOptions: false
          })
        } else {
          this.setData({ loadingOptions: false })
        }
      },
      fail: () => {
        this.setData({ loadingOptions: false })
      }
    })
  },

  onRefundTypeChange(e) {
    this.setData({
      refundType: e.detail.value,
      refundAmount: e.detail.value === 'membership' ? '' : this.data.refundAmount,
      calculation: null,
      showCalculation: false,
      selectedOptionIndex: -1
    })
  },

  onRechargeSelect(e) {
    const index = parseInt(e.detail.value)
    const option = this.data.rechargeOptions[index]
    if (!option) return

    if (!option.can_refund) {
      wx.showToast({ title: option.reason || this.data.tRefundNotRefundable, icon: 'none' })
      return
    }

    this.setData({
      selectedOptionIndex: index,
      refundAmount: String(option.refundable_amount),
      calculation: null,
      showCalculation: false
    })
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

  async onCalculateTap() {
    const { refundType, refundAmount } = this.data

    if (!refundAmount || parseFloat(refundAmount) <= 0) {
      wx.showToast({ title: this.data.tRefundSelectAmountFirst, icon: 'none' })
      return
    }

    const token = getToken()
    if (!token) {
      wx.showToast({ title: this.data.tRefundLoginFirst, icon: 'none' })
      return
    }

    this.setData({ calculating: true })

    try {
      const res = await new Promise((resolve, reject) => {
        wx.request({
          url: `${API_BASE_URL}/api/refund/calculate`,
          method: 'POST',
          data: {
            refund_type: refundType,
            refund_amount: parseFloat(refundAmount),
            notify_admin: true
          },
          header: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          success: (res) => {
            if (res.statusCode === 200) resolve(res.data)
            else reject(new Error(res.data.error || this.data.tRefundCalcFail))
          },
          fail: () => reject(new Error(this.data.tRefundNetworkFail))
        })
      })

      if (res.success && res.calculation) {
        this.setData({
          calculation: res.calculation,
          showCalculation: true
        })

        wx.showToast({ title: this.data.tRefundCalcGenerated, icon: 'success' })
      } else {
        wx.showToast({ title: res.error || this.data.tRefundCalcFail, icon: 'none' })
      }
    } catch (e) {
      console.error('计算退款核算失败:', e)
      wx.showToast({ title: e.message || this.data.tRefundCalcFail, icon: 'none' })
    } finally {
      this.setData({ calculating: false })
    }
  },

  onCloseCalculation() {
    this.setData({ showCalculation: false })
  },

  onSubmit() {
    const { refundType, refundAmount, reason, suggestions, applicantName, applicantPhone, submitting } = this.data

    if (submitting) return

    if (!refundType) {
      wx.showToast({ title: this.data.tRefundSelectTypeFirst, icon: 'none' })
      return
    }

    if (refundType === 'recharge') {
      if (this.data.selectedOptionIndex < 0) {
        wx.showToast({ title: this.data.tRefundSelectRecordFirst, icon: 'none' })
        return
      }
    }

    if (!refundAmount || parseFloat(refundAmount) <= 0) {
      wx.showToast({ title: this.data.tRefundSelectAmountFirst, icon: 'none' })
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
