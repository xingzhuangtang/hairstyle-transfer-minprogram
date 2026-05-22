// pages/device/device.js
import { get, post } from '../../utils/request.js'

Page({
  data: {
    devices: [],
    loading: false
  },

  onLoad() {
    this.loadDevices()
  },

  onShow() {
    // 每次显示时刷新设备列表
    this.loadDevices()
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
          title: res.error || '加载失败',
          icon: 'none'
        })
      }
    } catch (e) {
      console.error('加载设备列表失败:', e)
      wx.showToast({
        title: '网络请求失败',
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

      wx.showLoading({ title: '绑定中...' })

      const res = await post('/api/device/bind', {
        device_id: deviceId,
        device_name: deviceName,
        device_type: deviceType
      })

      wx.hideLoading()

      if (res.success) {
        wx.showToast({
          title: '绑定成功',
          icon: 'success'
        })
        // 刷新设备列表
        this.loadDevices()
      } else {
        if (res.code === 'MAX_DEVICES_REACHED') {
          wx.showModal({
            title: '提示',
            content: '已达到最大设备绑定数量（2个），请先解绑不需要的设备',
            showCancel: false
          })
        } else if (res.code === 'DEVICE_ALREADY_BOUND') {
          wx.showToast({
            title: '该设备已被其他账户绑定',
            icon: 'none'
          })
        } else {
          wx.showToast({
            title: res.error || '绑定失败',
            icon: 'none'
          })
        }
      }
    } catch (e) {
      wx.hideLoading()
      console.error('绑定设备失败:', e)
      wx.showToast({
        title: '绑定失败，请重试',
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
      title: '确认解绑',
      content: '解绑后该设备需重新绑定才能使用，确定要解绑吗？',
      confirmText: '解绑',
      confirmColor: '#ff4d4f',
      success: async (res) => {
        if (res.confirm) {
          try {
            wx.showLoading({ title: '解绑中...' })

            const result = await post('/api/device/unbind', {
              device_id: deviceId
            })

            wx.hideLoading()

            if (result.success) {
              wx.showToast({
                title: '解绑成功',
                icon: 'success'
              })
              // 刷新设备列表
              this.loadDevices()
            } else {
              if (result.code === 'MIN_DEVICES_REQUIRED') {
                wx.showToast({
                  title: '至少需要保留一个设备',
                  icon: 'none'
                })
              } else {
                wx.showToast({
                  title: result.error || '解绑失败',
                  icon: 'none'
                })
              }
            }
          } catch (e) {
            wx.hideLoading()
            console.error('解绑设备失败:', e)
            wx.showToast({
              title: '解绑失败，请重试',
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
    const brand = systemInfo.brand || '未知品牌'
    const model = systemInfo.model || '未知型号'
    return `${brand} ${model}`
  },

  /**
   * 格式化日期
   */
  formatDate(dateStr) {
    if (!dateStr) return '未知'
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
