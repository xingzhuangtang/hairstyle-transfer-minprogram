const { applyRefund } = require('../../api/refund.js')
const { getToken } = require('../../utils/storage.js')

Page({
  data: {
    refundType: 'recharge',
    refundAmount: '',
    reason: '',
    suggestions: '',
    applicantName: '',
    applicantPhone: '',
    submitting: false,
    userInfo: null
  },

  onLoad() {
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
      wx.showToast({ title: '请选择退款类型', icon: 'none' })
      return
    }

    if (!refundAmount || parseFloat(refundAmount) <= 0) {
      wx.showToast({ title: '请输入退款金额', icon: 'none' })
      return
    }

    if (!reason || reason.trim().length === 0) {
      wx.showToast({ title: '请填写退款原因', icon: 'none' })
      return
    }

    if (!applicantName || applicantName.trim().length === 0) {
      wx.showToast({ title: '请填写姓名', icon: 'none' })
      return
    }

    if (!applicantPhone || !/^1\d{10}$/.test(applicantPhone)) {
      wx.showToast({ title: '请填写正确的手机号', icon: 'none' })
      return
    }

    // 检查 token
    const token = getToken()
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' })
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
        wx.showToast({ title: '申请提交成功', icon: 'success' })
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({ title: res.error || '提交失败', icon: 'none' })
      }
    }).catch(err => {
      console.error('提交退款申请失败:', err)
      wx.showToast({ title: err.error || '网络错误，请稍后重试', icon: 'none' })
    }).finally(() => {
      this.setData({ submitting: false })
    })
  }
})
