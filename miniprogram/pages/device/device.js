// pages/device/device.js
import { get, post } from '../../utils/request.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    devices: [],
    loading: false,
    // i18n
    tDeviceMyDevices: '',
    tDevicePrimary: '',
    tDeviceIdLabel: '',
    tDeviceBoundTime: '',
    tDeviceUnbind: '',
    tDeviceEmptyLoggedIn: '',
    tDeviceEmptyGuest: '',
    tDeviceGoLogin: '',
    tDeviceBindCurrent: '',
    tDeviceBindNew: '',
    tDeviceMaxDevicesHint: '',
    tDeviceTipsTitle: '',
    tDeviceTip1LoggedIn: '',
    tDeviceTip2LoggedIn: '',
    tDeviceTip3LoggedIn: '',
    tDeviceTip4LoggedIn: '',
    tDeviceTip1Guest: '',
    tDeviceTip2Guest: '',
    tDeviceTip3Guest: '',
    tDeviceBinding: '',
    tDeviceBindSuccess: '',
    tDeviceBindFail: '',
    tDeviceMaxDevicesReached: '',
    tDeviceAlreadyBound: '',
    tDeviceConfirmUnbind: '',
    tDeviceUnbindContent: '',
    tDeviceUnbindBtn: '',
    tDeviceUnbinding: '',
    tDeviceUnbindSuccess: '',
    tDeviceMinDevicesRequired: '',
    tDeviceUnbindFail: '',
    tDeviceLoadFail: '',
    tDeviceUnknown: ''
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    this.loadDevices()
  },

  onShow() {
    this._loadI18n()
    // 每次显示时刷新设备列表
    this.loadDevices()
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tDeviceMyDevices: t('device.myDevices'),
      tDevicePrimary: t('device.primaryDevice'),
      tDeviceIdLabel: t('device.deviceIdLabel'),
      tDeviceBoundTime: t('device.boundTime'),
      tDeviceUnbind: t('device.unbind'),
      tDeviceEmptyLoggedIn: t('device.emptyLoggedIn'),
      tDeviceEmptyGuest: t('device.emptyGuest'),
      tDeviceGoLogin: t('device.goLogin'),
      tDeviceBindCurrent: t('device.bindCurrent'),
      tDeviceBindNew: t('device.bindNew'),
      tDeviceMaxDevicesHint: t('device.maxDevicesHint'),
      tDeviceTipsTitle: t('device.tipsTitle'),
      tDeviceTip1LoggedIn: t('device.tip1LoggedIn'),
      tDeviceTip2LoggedIn: t('device.tip2LoggedIn'),
      tDeviceTip3LoggedIn: t('device.tip3LoggedIn'),
      tDeviceTip4LoggedIn: t('device.tip4LoggedIn'),
      tDeviceTip1Guest: t('device.tip1Guest'),
      tDeviceTip2Guest: t('device.tip2Guest'),
      tDeviceTip3Guest: t('device.tip3Guest'),
      tDeviceBinding: t('device.binding'),
      tDeviceBindSuccess: t('device.bindSuccess'),
      tDeviceBindFail: t('device.bindFail'),
      tDeviceMaxDevicesReached: t('device.maxDevicesReached'),
      tDeviceAlreadyBound: t('device.deviceAlreadyBound'),
      tDeviceConfirmUnbind: t('device.confirmUnbind'),
      tDeviceUnbindContent: t('device.unbindContent'),
      tDeviceUnbindBtn: t('device.unbindBtn'),
      tDeviceUnbinding: t('device.unbinding'),
      tDeviceUnbindSuccess: t('device.unbindSuccess'),
      tDeviceMinDevicesRequired: t('device.minDevicesRequired'),
      tDeviceUnbindFail: t('device.unbindFail'),
      tDeviceLoadFail: t('device.loadFail'),
      tDeviceUnknown: t('common.unknown')
    })
    this._updateNavTitle()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
    })
  },

  _updateNavTitle() {
    app.setNavTitle(this, 'device.title')
  },

  /**
   * 加载设备列表
   */
  async loadDevices() {
    this.setData({ loading: true })

    try {
      const res = await get('/api/device/list')

      if (res.success) {
        // 格式化时间显示
        const devices = res.devices.map(device => ({
          ...device,
          bound_at: this.formatDate(device.bound_at),
          last_active_at: this.formatDate(device.last_active_at)
        }))

        this.setData({
          devices,
          isGuest: res.is_guest || false
        })
      } else {
        wx.showToast({
          title: res.error || this.data.tDeviceLoadFail,
          icon: 'none'
        })
      }
    } catch (e) {
      console.error('加载设备列表失败:', e)
      wx.showToast({
        title: this.data.tDeviceLoadFail,
        icon: 'none'
      })
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 绑定当前设备
   */
  async bindCurrentDevice() {
    try {
      // 获取系统信息
      const systemInfo = wx.getSystemInfoSync()

      // 生成设备 ID（基于系统信息生成固定 ID）
      const deviceId = this.generateDeviceId(systemInfo)

      // 检测设备类型
      const deviceType = this.detectDeviceType(systemInfo)

      // 生成设备名称
      const deviceName = this.generateDeviceName(systemInfo)

      wx.showLoading({ title: this.data.tDeviceBinding })

      const res = await post('/api/device/bind', {
        device_id: deviceId,
        device_name: deviceName,
        device_type: deviceType
      })

      wx.hideLoading()

      if (res.success) {
        wx.showToast({
          title: this.data.tDeviceBindSuccess,
          icon: 'success'
        })
        // 刷新设备列表
        this.loadDevices()
      } else {
        if (res.code === 'MAX_DEVICES_REACHED') {
          wx.showModal({
            title: this.data.tDeviceConfirmUnbind,
            content: this.data.tDeviceMaxDevicesReached,
            showCancel: false
          })
        } else if (res.code === 'DEVICE_ALREADY_BOUND') {
          wx.showToast({
            title: this.data.tDeviceAlreadyBound,
            icon: 'none'
          })
        } else {
          wx.showToast({
            title: res.error || this.data.tDeviceBindFail,
            icon: 'none'
          })
        }
      }
    } catch (e) {
      wx.hideLoading()
      console.error('绑定设备失败:', e)
      wx.showToast({
        title: this.data.tDeviceBindFail,
        icon: 'none'
      })
    }
  },

  /**
   * 解绑设备
   */
  async unbindDevice(e) {
    const deviceId = e.currentTarget.dataset.deviceId

    wx.showModal({
      title: this.data.tDeviceConfirmUnbind,
      content: this.data.tDeviceUnbindContent,
      confirmText: this.data.tDeviceUnbindBtn,
      confirmColor: '#ff4d4f',
      success: async (res) => {
        if (res.confirm) {
          try {
            wx.showLoading({ title: this.data.tDeviceUnbinding })

            const result = await post('/api/device/unbind', {
              device_id: deviceId
            })

            wx.hideLoading()

            if (result.success) {
              wx.showToast({
                title: this.data.tDeviceUnbindSuccess,
                icon: 'success'
              })
              // 刷新设备列表
              this.loadDevices()
            } else {
              if (result.code === 'MIN_DEVICES_REQUIRED') {
                wx.showToast({
                  title: this.data.tDeviceMinDevicesRequired,
                  icon: 'none'
                })
              } else {
                wx.showToast({
                  title: result.error || this.data.tDeviceUnbindFail,
                  icon: 'none'
                })
              }
            }
          } catch (e) {
            wx.hideLoading()
            console.error('解绑设备失败:', e)
            wx.showToast({
              title: this.data.tDeviceUnbindFail,
              icon: 'none'
            })
          }
        }
      }
    })
  },

  /**
   * 生成设备 ID（基于系统信息生成固定不变的 ID）
   */
  generateDeviceId(systemInfo) {
    // 使用系统信息生成固定设备 ID
    const uniqueStr = `${systemInfo.brand}-${systemInfo.model}-${systemInfo.system}-${systemInfo.platform}`
    // 简单哈希生成固定 ID
    let hash = 0
    for (let i = 0; i < uniqueStr.length; i++) {
      const char = uniqueStr.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash // Convert to 32bit integer
    }
    return `device_${Math.abs(hash).toString(16).padStart(8, '0')}`
  },

  /**
   * 检测设备类型
   */
  detectDeviceType(systemInfo) {
    const model = systemInfo.model.toLowerCase()
    const platform = systemInfo.platform

    if (platform === 'ios' || platform === 'android') {
      if (model.includes('ipad') || model.includes('tablet')) {
        return 'tablet'
      }
      return 'mobile'
    }

    return 'desktop'
  },

  /**
   * 生成设备名称
   */
  generateDeviceName(systemInfo) {
    const brand = systemInfo.brand || this.data.tDeviceUnknown
    const model = systemInfo.model || this.data.tDeviceUnknown
    return `${brand} ${model}`
  },

  /**
   * 格式化日期
   */
  formatDate(dateStr) {
    if (!dateStr) return this.data.tDeviceUnknown
    const date = new Date(dateStr)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}`
  },

  /**
   * 跳转到登录页
   */
  goToLogin() {
    wx.navigateTo({
      url: '/pages/login/login'
    })
  }
})
