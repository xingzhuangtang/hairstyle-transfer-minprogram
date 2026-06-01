// pages/settings/settings.js
import { refreshUserInfo, sendVerificationCode } from '../../utils/auth.js'
import { put, uploadFile, post } from '../../utils/request.js'

Page({
  data: {
    avatarUrl: '',
    nickname: '',
    originalNickname: '',
    originalAvatarUrl: '',
    saving: false,
    hasChanged: false,
    userId: '',
    phone: '',
    showChangePhoneModal: false,
    changePhone: '',
    changeCode: '',
    changeCounting: false,
    changeCountDown: 60,
    changeTimer: null,
    changeLoading: false
  },

  onLoad() {
    this.loadUserInfo()
  },

  onUnload() {
    if (this.data.changeTimer) {
      clearInterval(this.data.changeTimer)
    }
  },

  /**
   * 加载用户当前信息
   */
  async loadUserInfo() {
    try {
      const res = await refreshUserInfo()
      if (res.success) {
        const user = res.user
        this.setData({
          avatarUrl: user.avatar_url || '',
          nickname: user.nickname || '',
          originalAvatarUrl: user.avatar_url || '',
          originalNickname: user.nickname || '',
          userId: user.device_id || '',
          phone: user.phone || ''
        })
      }
    } catch (e) {
      console.error('加载用户信息失败:', e)
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
    }
  },

  /**
   * 选择头像
   */
  chooseAvatar() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0]
        console.log('选择图片成功:', tempFilePath)

        // 先显示预览
        this.setData({
          avatarUrl: tempFilePath,
          hasChanged: true
        })

        // 上传到服务器
        this.uploadAvatar(tempFilePath)
      },
      fail: (err) => {
        console.error('选择图片失败:', err)
        if (err.errMsg && !err.errMsg.includes('cancel')) {
          wx.showToast({
            title: '选择失败',
            icon: 'none'
          })
        }
      }
    })
  },

  /**
   * 上传头像
   */
  async uploadAvatar(filePath) {
    try {
      // 使用封装的 uploadFile 函数
      const data = await uploadFile(filePath)

      if (data.success && data.url) {
        this.setData({
          avatarUrl: data.url,
          hasChanged: true
        })
        wx.showToast({
          title: '上传成功',
          icon: 'success'
        })
      } else {
        wx.showToast({
          title: data.error || '上传失败',
          icon: 'none'
        })
        // 恢复原头像
        this.setData({
          avatarUrl: this.data.originalAvatarUrl
        })
      }
    } catch (e) {
      console.error('上传失败:', e)
      wx.showToast({
        title: '上传失败',
        icon: 'none'
      })
      this.setData({
        avatarUrl: this.data.originalAvatarUrl
      })
    }
  },

  /**
   * 昵称输入
   */
  onNicknameInput(e) {
    this.setData({
      nickname: e.detail.value,
      hasChanged: true
    })
  },

  /**
   * 保存设置
   */
  async saveSettings() {
    // 检查是否有改动
    if (!this.data.hasChanged) {
      wx.showToast({
        title: '暂无修改',
        icon: 'none'
      })
      return
    }

    // 验证昵称
    if (this.data.nickname && this.data.nickname.trim().length === 0) {
      wx.showToast({
        title: '昵称不能为空',
        icon: 'none'
      })
      return
    }

    this.setData({ saving: true })

    try {
      // 构建更新数据
      const updateData = {}
      if (this.data.nickname !== this.data.originalNickname) {
        updateData.nickname = this.data.nickname.trim()
      }
      if (this.data.avatarUrl !== this.data.originalAvatarUrl && !this.data.avatarUrl.startsWith('wxfile://')) {
        updateData.avatar_url = this.data.avatarUrl
      }

      // 如果没有需要更新的内容
      if (Object.keys(updateData).length === 0) {
        wx.showToast({
          title: '暂无修改',
          icon: 'none'
        })
        this.setData({ saving: false })
        return
      }

      // 调用更新接口
      const res = await put('/api/user/update', updateData)

      if (res.success) {
        wx.showToast({
          title: '保存成功',
          icon: 'success'
        })

        // 更新原始值
        this.setData({
          originalNickname: this.data.nickname,
          originalAvatarUrl: this.data.avatarUrl,
          hasChanged: false
        })

        // 延迟返回上一页
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: res.error || '保存失败',
          icon: 'none'
        })
      }
    } catch (e) {
      console.error('保存失败:', e)
      wx.showToast({
        title: '保存失败',
        icon: 'none'
      })
    } finally {
      this.setData({ saving: false })
    }
  },

  /**
   * 点击修改手机号
   */
  onChangePhone() {
    this.setData({
      showChangePhoneModal: true,
      changePhone: '',
      changeCode: '',
      changeCounting: false,
      changeCountDown: 60
    })
  },

  /**
   * 关闭修改手机号弹窗
   */
  onCloseChangePhoneModal() {
    if (this.data.changeTimer) {
      clearInterval(this.data.changeTimer)
    }
    this.setData({
      showChangePhoneModal: false,
      changePhone: '',
      changeCode: '',
      changeCounting: false,
      changeCountDown: 60,
      changeTimer: null
    })
  },

  /**
   * 手机号输入
   */
  onChangePhoneInput(e) {
    this.setData({ changePhone: e.detail.value })
  },

  /**
   * 验证码输入
   */
  onChangeCodeInput(e) {
    this.setData({ changeCode: e.detail.value })
  },

  /**
   * 验证手机号格式
   */
  validateChangePhone() {
    const phone = this.data.changePhone
    if (!phone) {
      wx.showToast({ title: '请输入手机号', icon: 'none' })
      return false
    }
    const phoneReg = /^1[3-9]\d{9}$/
    if (!phoneReg.test(phone)) {
      wx.showToast({ title: '手机号格式不正确', icon: 'none' })
      return false
    }
    return true
  },

  /**
   * 发送验证码
   */
  async sendChangeCode() {
    if (!this.validateChangePhone()) return

    try {
      const res = await sendVerificationCode(this.data.changePhone)
      if (res.success) {
        wx.showToast({ title: '验证码已发送', icon: 'success' })
        this.startChangeCountDown()
      } else {
        const errMsg = (typeof res.error === 'object') ? (res.error.error || res.error.message || '发送失败') : res.error
        wx.showToast({ title: errMsg || '发送失败', icon: 'none' })
      }
    } catch (e) {
      const errMsg = (typeof e === 'object') ? (e.error || e.message || '发送失败') : e
      wx.showToast({ title: errMsg, icon: 'none' })
    }
  },

  /**
   * 确认修改手机号
   */
  async confirmChangePhone() {
    const phone = this.data.changePhone
    const code = this.data.changeCode

    if (!phone) {
      wx.showToast({ title: '请输入手机号', icon: 'none' })
      return
    }
    if (!code) {
      wx.showToast({ title: '请输入验证码', icon: 'none' })
      return
    }

    // 检查是否与当前手机号相同
    if (phone === this.data.phone) {
      wx.showToast({ title: '与当前手机号相同，无需修改', icon: 'none' })
      return
    }

    this.setData({ changeLoading: true })

    try {
      const res = await post('/api/auth/bind-phone', {
        phone: phone,
        code: code
      })

      if (res.success) {
        wx.showToast({ title: '修改成功', icon: 'success' })
        await this.loadUserInfo()
        this.onCloseChangePhoneModal()
      } else {
        // 如果手机号已被其他用户绑定，走合并流程
        if (res.error && res.error.includes('已被绑定')) {
          wx.showModal({
            title: '账号合并提示',
            content: '该手机号已绑定其他账号，是否合并到该账号？',
            confirmText: '合并',
            cancelText: '取消',
            success: async (modalRes) => {
              if (modalRes.confirm) {
                const mergeRes = await post('/api/auth/merge-account', {
                  phone: phone,
                  code: code
                })
                if (mergeRes.success) {
                  wx.showToast({ title: '合并成功', icon: 'success' })
                  await this.loadUserInfo()
                  this.onCloseChangePhoneModal()
                } else {
                  const errMsg = (typeof mergeRes.error === 'object') ? (mergeRes.error.error || mergeRes.error.message || '合并失败') : mergeRes.error
                  wx.showToast({ title: errMsg || '合并失败', icon: 'none' })
                }
              }
            }
          })
        } else {
          const errMsg = (typeof res.error === 'object') ? (res.error.error || res.error.message || '操作失败') : res.error
          wx.showToast({ title: errMsg || '操作失败', icon: 'none' })
        }
      }
    } catch (e) {
      const errMsg = (typeof e === 'object') ? (e.error || e.message || '操作失败') : e
      wx.showToast({ title: errMsg, icon: 'none' })
    } finally {
      this.setData({ changeLoading: false })
    }
  },

  /**
   * 开始倒计时
   */
  startChangeCountDown() {
    this.setData({
      changeCounting: true,
      changeCountDown: 60
    })

    const timer = setInterval(() => {
      const countDown = this.data.changeCountDown - 1
      if (countDown <= 0) {
        clearInterval(timer)
        this.setData({
          changeCounting: false,
          changeCountDown: 60,
          changeTimer: null
        })
      } else {
        this.setData({ changeCountDown: countDown })
      }
    }, 1000)

    this.setData({ changeTimer: timer })
  }
})
