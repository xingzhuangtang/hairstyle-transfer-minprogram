// pages/settings/settings.js
import { refreshUserInfo } from '../../utils/auth.js'
import { put, uploadFile } from '../../utils/request.js'

Page({
  data: {
    avatarUrl: '',
    nickname: '',
    originalNickname: '',
    originalAvatarUrl: '',
    saving: false,
    hasChanged: false
  },

  onLoad() {
    this.loadUserInfo()
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
          originalNickname: user.nickname || ''
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
  }
})
