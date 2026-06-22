// pages/settings/settings.js
import { refreshUserInfo, sendVerificationCode } from '../../utils/auth.js'
import { put, uploadFile, post } from '../../utils/request.js'
import { getLocale, setLocale, getSupportedLocales, getLocaleDisplayName, onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

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
    changeLoading: false,
    // i18n
    localeOptions: [],
    localeIndex: 0,
    currentLocaleName: '',
    tSettingsLanguage: '',
    tCommonSave: '',
    tCommonCancel: '',
    tCommonConfirm: '',
    tSettingsChangePhone: '',
    tSettingsChangePhoneDesc: '',
    tSettingsPhonePlaceholder: '',
    tSettingsCodePlaceholder: '',
    tSettingsGetCode: '',
    tSettingsLoadFail: '',
    tSettingsSelectFail: '',
    tSettingsUploadSuccess: '',
    tSettingsUploadFail: '',
    tSettingsNoChange: '',
    tSettingsNicknameEmpty: '',
    tSettingsSaveSuccess: '',
    tSettingsSaveFail: '',
    tSettingsPhoneInput: '',
    tSettingsPhoneFormat: '',
    tSettingsCodeSent: '',
    tSettingsSendFail: '',
    tSettingsModifySuccess: '',
    tSettingsPhoneSame: '',
    tSettingsMergeTitle: '',
    tSettingsMergeContent: '',
    tSettingsMergeBtn: '',
    tSettingsMergeSuccess: '',
    tSettingsMergeFail: '',
    tSettingsOpFail: '',
    tLocaleChangedZh: '',
    tLocaleChangedEn: '',
    tSettingsAvatar: '',
    tSettingsClickChange: '',
    tSettingsNickname: '',
    tSettingsPhone: '',
    tSettingsUserId: '',
    tSettingsUnknown: '',
    tSettingsNotBound: '',
    tSettingsChange: '',
    tSettingsProfileTip: ''
  },

  onLoad() {
    this.initLocale()
    app.setNavTitle(this, 'settings.title')
    this.loadUserInfo()
  },

  onShow() {
    this.refreshLocaleDisplay()
    app.setNavTitle(this, 'settings.title')
  },

  onUnload() {
    if (this.data.changeTimer) {
      clearInterval(this.data.changeTimer)
    }
  },

  /**
   * 初始化语言设置
   */
  initLocale() {
    const locales = getSupportedLocales()
    const options = locales.map(l => ({
      value: l,
      label: getLocaleDisplayName(l)
    }))
    const current = getLocale()
    const index = locales.indexOf(current)

    this.setData({
      localeOptions: options,
      localeIndex: index >= 0 ? index : 0,
      currentLocaleName: getLocaleDisplayName(current)
    })

    this.loadTranslations()
  },

  /**
   * 加载当前语言的翻译
   */
  loadTranslations() {
    const app = getApp()
    const t = (key) => app.t(key)
    this.setData({
      tSettingsLanguage: t('settings.language'),
      tCommonSave: t('common.save'),
      tCommonCancel: t('common.cancel'),
      tCommonConfirm: t('common.confirm'),
      tSettingsNickname: t('settings.nickname'),
      tSettingsPhone: t('settings.phone'),
      tSettingsChangePhone: t('settings.changePhone'),
      tSettingsChangePhoneDesc: t('settings.changePhoneDesc'),
      tSettingsPhonePlaceholder: t('settings.phonePlaceholder'),
      tSettingsCodePlaceholder: t('settings.codePlaceholder'),
      tSettingsGetCode: t('common.getVerifyCode'),
      tSettingsLoadFail: t('common.loadFail'),
      tSettingsSelectFail: t('common.selectFail'),
      tSettingsUploadSuccess: t('common.uploadSuccess'),
      tSettingsUploadFail: t('common.uploadFail'),
      tSettingsNoChange: t('settings.noEdit'),
      tSettingsNicknameEmpty: t('settings.nicknameEmpty'),
      tSettingsSaveSuccess: t('common.saveSuccess'),
      tSettingsSaveFail: t('common.saveFail'),
      tSettingsPhoneInput: t('login.pleaseInputPhone'),
      tSettingsPhoneFormat: t('login.phoneFormatError'),
      tSettingsCodeSent: t('common.verifyCodeSent'),
      tSettingsSendFail: t('common.sendFail'),
      tSettingsModifySuccess: t('common.saveSuccess'),
      tSettingsPhoneSame: t('settings.phoneSame'),
      tSettingsMergeTitle: t('login.mergeTip'),
      tSettingsMergeContent: t('login.mergeContent'),
      tSettingsMergeBtn: t('common.merge'),
      tSettingsMergeSuccess: t('login.mergeSuccess'),
      tSettingsMergeFail: t('login.mergeFail'),
      tSettingsOpFail: t('common.fail'),
      tLocaleChangedZh: '语言已切换为中文',
      tLocaleChangedEn: 'Language switched to English',
      tSettingsAvatar: t('settings.avatar'),
      tSettingsClickChange: t('settings.clickChange'),
      tSettingsUserId: t('settings.userId'),
      tSettingsUnknown: t('common.unknown'),
      tSettingsNotBound: t('settings.notBound'),
      tSettingsChange: t('settings.change'),
      tSettingsProfileTip: t('settings.profileTip')
    })
  },

  /**
   * 刷新语言显示
   */
  refreshLocaleDisplay() {
    const current = getLocale()
    const locales = getSupportedLocales()
    const index = locales.indexOf(current)

    this.setData({
      localeIndex: index >= 0 ? index : 0,
      currentLocaleName: getLocaleDisplayName(current)
    })

    this.loadTranslations()
  },

  /**
   * 语言切换
   */
  onLocaleChange(e) {
    const index = parseInt(e.detail.value)
    const locales = getSupportedLocales()
    const newLocale = locales[index]

    if (newLocale && newLocale !== getLocale()) {
      setLocale(newLocale)
      this.refreshLocaleDisplay()

      const app = getApp()
      app.setTabBarLabels()
      app.setNavTitle(this, 'settings.title')

      wx.showToast({
        title: newLocale === 'zh-CN' ? this.data.tLocaleChangedZh : this.data.tLocaleChangedEn,
        icon: 'success'
      })
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
        title: this.data.tSettingsLoadFail,
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

        this.setData({
          avatarUrl: tempFilePath,
          hasChanged: true
        })

        this.uploadAvatar(tempFilePath)
      },
      fail: (err) => {
        console.error('选择图片失败:', err)
        if (err.errMsg && !err.errMsg.includes('cancel')) {
          wx.showToast({
            title: this.data.tSettingsSelectFail,
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
      const data = await uploadFile(filePath)

      if (data.success && data.url) {
        this.setData({
          avatarUrl: data.url,
          hasChanged: true
        })
        wx.showToast({
          title: this.data.tSettingsUploadSuccess,
          icon: 'success'
        })
      } else {
        wx.showToast({
          title: data.error || this.data.tSettingsUploadFail,
          icon: 'none'
        })
        this.setData({
          avatarUrl: this.data.originalAvatarUrl
        })
      }
    } catch (e) {
      console.error('上传失败:', e)
      wx.showToast({
        title: this.data.tSettingsUploadFail,
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
    if (!this.data.hasChanged) {
      wx.showToast({
        title: this.data.tSettingsNoChange,
        icon: 'none'
      })
      return
    }

    if (this.data.nickname && this.data.nickname.trim().length === 0) {
      wx.showToast({
        title: this.data.tSettingsNicknameEmpty,
        icon: 'none'
      })
      return
    }

    this.setData({ saving: true })

    try {
      const updateData = {}
      if (this.data.nickname !== this.data.originalNickname) {
        updateData.nickname = this.data.nickname.trim()
      }
      if (this.data.avatarUrl !== this.data.originalAvatarUrl && !this.data.avatarUrl.startsWith('wxfile://')) {
        updateData.avatar_url = this.data.avatarUrl
      }

      if (Object.keys(updateData).length === 0) {
        wx.showToast({
          title: this.data.tSettingsNoChange,
          icon: 'none'
        })
        this.setData({ saving: false })
        return
      }

      const res = await put('/api/user/update', updateData)

      if (res.success) {
        wx.showToast({
          title: this.data.tSettingsSaveSuccess,
          icon: 'success'
        })

        this.setData({
          originalNickname: this.data.nickname,
          originalAvatarUrl: this.data.avatarUrl,
          hasChanged: false
        })

        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: res.error || this.data.tSettingsSaveFail,
          icon: 'none'
        })
      }
    } catch (e) {
      console.error('保存失败:', e)
      wx.showToast({
        title: this.data.tSettingsSaveFail,
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
      wx.showToast({ title: this.data.tSettingsPhoneInput, icon: 'none' })
      return false
    }
    const phoneReg = /^1[3-9]\d{9}$/
    if (!phoneReg.test(phone)) {
      wx.showToast({ title: this.data.tSettingsPhoneFormat, icon: 'none' })
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
        wx.showToast({ title: this.data.tSettingsCodeSent, icon: 'success' })
        this.startChangeCountDown()
      } else {
        const errMsg = (typeof res.error === 'object') ? (res.error.error || res.error.message || this.data.tSettingsSendFail) : res.error
        wx.showToast({ title: errMsg || this.data.tSettingsSendFail, icon: 'none' })
      }
    } catch (e) {
      const errMsg = (typeof e === 'object') ? (e.error || e.message || this.data.tSettingsSendFail) : e
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
      wx.showToast({ title: this.data.tSettingsPhoneInput, icon: 'none' })
      return
    }
    if (!code) {
      wx.showToast({ title: this.data.tSettingsCodePlaceholder, icon: 'none' })
      return
    }

    if (phone === this.data.phone) {
      wx.showToast({ title: this.data.tSettingsPhoneSame, icon: 'none' })
      return
    }

    this.setData({ changeLoading: true })

    try {
      const res = await post('/api/auth/bind-phone', {
        phone: phone,
        code: code
      })

      if (res.success) {
        wx.showToast({ title: this.data.tSettingsModifySuccess, icon: 'success' })
        await this.loadUserInfo()
        this.onCloseChangePhoneModal()
      } else {
        if (res.error && res.error.includes('已被绑定')) {
          wx.showModal({
            title: this.data.tSettingsMergeTitle,
            content: this.data.tSettingsMergeContent,
            confirmText: this.data.tSettingsMergeBtn,
            cancelText: this.data.tCommonCancel,
            success: async (modalRes) => {
              if (modalRes.confirm) {
                const mergeRes = await post('/api/auth/merge-account', {
                  phone: phone,
                  code: code
                })
                if (mergeRes.success) {
                  wx.showToast({ title: this.data.tSettingsMergeSuccess, icon: 'success' })
                  await this.loadUserInfo()
                  this.onCloseChangePhoneModal()
                } else {
                  const errMsg = (typeof mergeRes.error === 'object') ? (mergeRes.error.error || mergeRes.error.message || this.data.tSettingsMergeFail) : mergeRes.error
                  wx.showToast({ title: errMsg || this.data.tSettingsMergeFail, icon: 'none' })
                }
              }
            }
          })
        } else {
          const errMsg = (typeof res.error === 'object') ? (res.error.error || res.error.message || this.data.tSettingsOpFail) : res.error
          wx.showToast({ title: errMsg || this.data.tSettingsOpFail, icon: 'none' })
        }
      }
    } catch (e) {
      const errMsg = (typeof e === 'object') ? (e.error || e.message || this.data.tSettingsOpFail) : e
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
