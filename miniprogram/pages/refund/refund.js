const { applyRefund } = require('../../api/refund.js')
const { getToken } = require('../../utils/storage.js')
const { API_BASE_URL } = require('../../utils/constants.js')

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
    // 核算清单相关
    calculation: null,
    calculating: false,
    showCalculation: false,
    // 充值选项下拉框
    rechargeOptions: [],
    rechargePickerRange: [],
    selectedOptionIndex: -1,
    loadingOptions: true
  },

  onLoad() {
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

  /**
   * 加载充值退款选项
   */
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

  /**
   * 下拉框选择充值记录
   */
  onRechargeSelect(e) {
    const index = parseInt(e.detail.value)
    const option = this.data.rechargeOptions[index]
    if (!option) return

    if (!option.can_refund) {
      wx.showToast({ title: option.reason || '该笔充值不可退', icon: 'none' })
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

  /**
   * 点击"查看退款核算清单"按钮
   */
  async onCalculateTap() {
    const { refundType, refundAmount } = this.data

    if (!refundAmount || parseFloat(refundAmount) <= 0) {
      wx.showToast({ title: '请先选择退款金额', icon: 'none' })
      return
    }

    const token = getToken()
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' })
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
            else reject(new Error(res.data.error || '计算失败'))
          },
          fail: (err) => reject(new Error('网络请求失败'))
        })
      })

      if (res.success && res.calculation) {
        this.setData({
          calculation: res.calculation,
          showCalculation: true
        })

        wx.showToast({ title: '核算清单已生成', icon: 'success' })
      } else {
        wx.showToast({ title: res.error || '计算失败', icon: 'none' })
      }
    } catch (e) {
      console.error('计算退款核算失败:', e)
      wx.showToast({ title: e.message || '计算失败', icon: 'none' })
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
      wx.showToast({ title: '请选择退款类型', icon: 'none' })
      return
    }

    if (refundType === 'recharge') {
      if (this.data.selectedOptionIndex < 0) {
        wx.showToast({ title: '请选择要退款的充值记录', icon: 'none' })
        return
      }
    }

    if (!refundAmount || parseFloat(refundAmount) <= 0) {
      wx.showToast({ title: '请选择退款金额', icon: 'none' })
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
