// pages/History/history.js
import { getMemberInfo } from '../../api/member.js'
import { getHistoryRecords } from '../../api/hair.js'

// 服务类型映射
const SERVICE_TYPE_MAP = {
  hair_segment: '发型提取',
  face_merge: '发型融合',
  sketch: '素描转换',
  combined: '一键生成',
  fm_step: '融合步骤',
  sk_step: '素描步骤'
}

Page({
  data: {
    isVip: false,
    remainingDays: 0,
    records: [],
    loading: false,
    page: 1,
    pageSize: 20,
    hasMore: true,
    countdownTimer: null,
    canvasWidth: 1080,
    canvasHeight: 2000
  },

  onLoad() {
    this.loadMemberInfo()
  },

  onShow() {
    this.loadMemberInfo()
    this.startCountdownTimer()
  },

  onHide() {
    this.stopCountdownTimer()
  },

  onUnload() {
    this.stopCountdownTimer()
  },

  async loadMemberInfo() {
    try {
      const res = await getMemberInfo()
      console.log('会员信息API返回:', res)
      
      if (res.member_level !== undefined) {
        // 后端返回的是 member_level: 'vip' 或 'normal'
        const isVip = res.member_level === 'vip'
        const remainingDays = res.remaining_days || 0

        console.log('isVip:', isVip, 'remainingDays:', remainingDays)
        this.setData({ isVip, remainingDays })

        if (isVip) {
          this.loadHistoryRecords()
        }
      }
    } catch (e) {
      console.error('加载会员信息失败:', e)
    }
  },

  async loadHistoryRecords(refresh = false) {
    if (this.data.loading) return

    const currentPage = refresh ? 1 : this.data.page

    try {
      this.setData({ loading: true })

      const res = await getHistoryRecords(currentPage, this.data.pageSize)

      if (res.records !== undefined) {
        console.log('历史记录API返回:', res)
        
        const newRecords = res.records.map(record => {
          const resultImage = record.result_image || record.result_url || ''
          const sketchImage = record.sketch_url || ''
          
          // 计算倒计时
          let countdownText = ''
          let countdownClass = 'valid'
          let remainingHours = 0
          
          if (record.expire_at) {
            const expireDate = new Date(record.expire_at)
            const now = new Date()
            const diffMs = expireDate - now
            
            if (diffMs <= 0) {
              countdownText = '已过期'
              countdownClass = 'expired'
            } else {
              const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
              const diffDays = Math.floor(diffHours / 24)
              remainingHours = diffHours
              
              if (diffDays >= 1) {
                countdownText = `剩余${diffDays}天`
                if (diffDays <= 3) {
                  countdownClass = 'warning'
                }
              } else {
                countdownText = `剩余${diffHours}小时`
                countdownClass = 'urgent'
              }
            }
          }
          
          console.log('记录ID:', record.id, 'result_url:', record.result_url, 'sketch_url:', sketchImage)
          
          return {
            ...record,
            id: record.id,
            result_image: resultImage,
            sketch_image: sketchImage,
            has_sketch: !!sketchImage,
            service_type: record.service_type || 'combined',
            service_type_text: SERVICE_TYPE_MAP[record.service_type] || '发型迁移',
            is_expired: record.is_expired || false,
            created_at: this.formatDate(record.created_at),
            countdown_text: countdownText,
            countdown_class: countdownClass,
            remaining_hours: remainingHours
          }
        })

        console.log('处理后的记录:', newRecords)
        
        this.setData({
          records: refresh ? newRecords : [...this.data.records, ...newRecords],
          page: currentPage + 1,
          hasMore: res.records.length === this.data.pageSize,
          loading: false
        })
      } else {
        console.error('API返回错误:', res)
        this.setData({ loading: false })
      }
    } catch (e) {
      console.error('加载历史记录失败:', e)
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  loadMore() {
    if (!this.data.hasMore && !this.data.loading) {
      wx.showToast({ title: '没有更多了', icon: 'none' })
      return
    }
    this.loadHistoryRecords(false)
  },

  viewDetail(e) {
    const { id } = e.currentTarget.dataset
    
    const record = this.data.records.find(r => r.id === id)
    if (!record) return
    
    if (record.is_expired) {
      wx.showToast({ title: '记录已过期', icon: 'none' })
      return
    }

    // 弹出操作菜单
    const menuItems = ['预览所有图片']
    if (record.result_image) menuItems.push('下载原图')
    if (record.sketch_image) menuItems.push('下载素描')
    if (record.result_image && record.sketch_image) menuItems.push('保存合并图片')
    menuItems.push('删除记录')

    wx.showActionSheet({
      itemList: menuItems,
      success: (res) => {
        const action = menuItems[res.tapIndex]
        
        if (action === '预览所有图片') {
          const imageUrls = []
          if (record.result_image) imageUrls.push(record.result_image)
          if (record.sketch_image) imageUrls.push(record.sketch_image)
          if (imageUrls.length > 0) {
            wx.previewImage({
              urls: imageUrls,
              current: imageUrls[0]
            })
          }
        } else if (action === '下载原图') {
          this.downloadImage(record.result_image, '原图')
        } else if (action === '下载素描') {
          this.downloadImage(record.sketch_image, '素描')
        } else if (action === '保存合并图片') {
          this.saveCombinedImage(record)
        } else if (action === '删除记录') {
          this.deleteRecord({ currentTarget: { dataset: { id } } })
        }
      }
    })
  },

  saveCombinedImage(record) {
    wx.showLoading({ title: '生成合并图片中...' })

    const images = []
    if (record.result_image) images.push({ url: record.result_image, label: '结果' })
    if (record.sketch_image) images.push({ url: record.sketch_image, label: '素描' })

    const TARGET_WIDTH = 1080
    const LABEL_HEIGHT = 60
    const GAP = 20
    const downloaded = []

    let completed = 0
    const checkAllDone = () => {
      completed++
      if (completed < images.length) return

      let totalHeight = 0
      const drawInfos = []
      for (let i = 0; i < downloaded.length; i++) {
        const info = downloaded[i]
        const scale = TARGET_WIDTH / info.width
        const drawHeight = Math.round(info.height * scale)
        drawInfos.push({
          path: info.path,
          label: info.label,
          y: totalHeight,
          drawWidth: TARGET_WIDTH,
          drawHeight: drawHeight
        })
        totalHeight += drawHeight + LABEL_HEIGHT
        if (i < downloaded.length - 1) totalHeight += GAP
      }

      const canvasWidth = TARGET_WIDTH
      const canvasHeight = totalHeight

      this.setData({
        canvasWidth: canvasWidth,
        canvasHeight: canvasHeight
      }, () => {
        const ctx = wx.createCanvasContext('combinedCanvas', this)

        ctx.setFillStyle('#ffffff')
        ctx.fillRect(0, 0, canvasWidth, canvasHeight)

        for (const d of drawInfos) {
          ctx.drawImage(d.path, 0, d.y, d.drawWidth, d.drawHeight)

          ctx.setFillStyle('rgba(0, 0, 0, 0.5)')
          ctx.fillRect(0, d.y + d.drawHeight, canvasWidth, LABEL_HEIGHT)
          ctx.setFillStyle('#ffffff')
          ctx.setFontSize(28)
          ctx.setTextAlign('center')
          ctx.fillText(d.label, canvasWidth / 2, d.y + d.drawHeight + 40)
        }

        ctx.draw(false, () => {
          setTimeout(() => {
            wx.canvasToTempFilePath({
              canvasId: 'combinedCanvas',
              x: 0,
              y: 0,
              width: canvasWidth,
              height: canvasHeight,
              destWidth: canvasWidth,
              destHeight: canvasHeight,
              fileType: 'jpg',
              quality: 0.92,
              success: (res) => {
                wx.saveImageToPhotosAlbum({
                  filePath: res.tempFilePath,
                  success: () => {
                    wx.hideLoading()
                    wx.showToast({ title: '合并图片已保存到相册', icon: 'success' })
                  },
                  fail: () => {
                    wx.hideLoading()
                    wx.showToast({ title: '保存失败', icon: 'none' })
                  }
                })
              },
              fail: () => {
                wx.hideLoading()
                wx.showToast({ title: '生成失败', icon: 'none' })
              }
            }, this)
          }, 500)
        })
      })
    }

    images.forEach((img, idx) => {
      wx.downloadFile({
        url: img.url,
        success: (res) => {
          if (res.statusCode !== 200) {
            completed++
            return
          }
          wx.getImageInfo({
            src: res.tempFilePath,
            success: (info) => {
              downloaded[idx] = {
                path: res.tempFilePath,
                width: info.width,
                height: info.height,
                label: img.label
              }
              checkAllDone()
            },
            fail: () => {
              completed++
            }
          })
        },
        fail: () => {
          completed++
        }
      })
    })
  },

  downloadCombinedImage(e) {
    const { id } = e.currentTarget.dataset
    const record = this.data.records.find(r => r.id === id)
    if (!record) return

    if (record.is_expired) {
      wx.showToast({ title: '记录已过期，无法下载', icon: 'none' })
      return
    }

    if (!record.result_image && !record.sketch_image) {
      wx.showToast({ title: '暂无图片', icon: 'none' })
      return
    }

    // 提示用户长按保存
    wx.showModal({
      title: '下载图片',
      content: '点击"预览所有图片"后，长按图片即可保存到相册',
      confirmText: '去预览',
      cancelText: '知道了',
      success: (res) => {
        if (res.confirm) {
          this.viewDetail({ currentTarget: { dataset: { id } } })
        }
      }
    })
  },

  onImageError(e) {
    const index = e.currentTarget.dataset.index
    const records = this.data.records
    if (records[index]) {
      records[index].result_image = '/images/empty-device.svg'
      this.setData({ records })
    }
  },

  onSketchError(e) {
    const index = e.currentTarget.dataset.index
    const records = this.data.records
    if (records[index]) {
      records[index].sketch_image = '/images/empty-device.svg'
      this.setData({ records })
    }
  },

  showDownloadMenu(e) {
    const { id, type } = e.currentTarget.dataset
    const record = this.data.records.find(r => r.id === id)
    if (!record) return

    if (record.is_expired) {
      wx.showToast({ title: '记录已过期，无法下载', icon: 'none' })
      return
    }

    const imageUrl = type === 'sketch' ? record.sketch_image : record.result_image
    if (!imageUrl) {
      wx.showToast({ title: '暂无图片', icon: 'none' })
      return
    }

    wx.showActionSheet({
      itemList: ['预览图片', '下载到手机'],
      success: (res) => {
        if (res.tapIndex === 0) {
          // 预览
          wx.previewImage({
            urls: [imageUrl],
            current: imageUrl
          })
        } else if (res.tapIndex === 1) {
          // 下载
          this.downloadImage(imageUrl, type === 'sketch' ? '素描' : '结果')
        }
      }
    })
  },

  downloadImage(imageUrl, imageType) {
    wx.showLoading({ title: '下载中...' })
    
    wx.downloadFile({
      url: imageUrl,
      success: (res) => {
        if (res.statusCode === 200) {
          wx.saveImageToPhotosAlbum({
            filePath: res.tempFilePath,
            success: () => {
              wx.hideLoading()
              wx.showToast({ title: `${imageType}图片已保存到相册`, icon: 'success' })
            },
            fail: (err) => {
              wx.hideLoading()
              if (err.errMsg && err.errMsg.includes('auth deny')) {
                wx.showModal({
                  title: '提示',
                  content: '需要授权访问相册',
                  confirmText: '去授权',
                  success: (modalRes) => {
                    if (modalRes.confirm) {
                      wx.openSetting()
                    }
                  }
                })
              } else {
                wx.showToast({ title: '保存失败', icon: 'none' })
              }
            }
          })
        } else {
          wx.hideLoading()
          wx.showToast({ title: '下载失败', icon: 'none' })
        }
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '下载失败', icon: 'none' })
      }
    })
  },

  goToMember() {
    wx.switchTab({ url: '/pages/profile/profile' })
  },

  startCountdownTimer() {
    this.stopCountdownTimer()
    
    this.data.countdownTimer = setInterval(() => {
      this.updateCountdowns()
    }, 60 * 60 * 1000) // 每小时更新一次
  },

  stopCountdownTimer() {
    if (this.data.countdownTimer) {
      clearInterval(this.data.countdownTimer)
      this.setData({ countdownTimer: null })
    }
  },

  updateCountdowns() {
    const records = this.data.records.map(record => {
      if (record.expire_at) {
        const expireDate = new Date(record.expire_at)
        const now = new Date()
        const diffMs = expireDate - now
        
        let countdownText = ''
        let countdownClass = 'valid'
        let remainingHours = 0
        
        if (diffMs <= 0) {
          countdownText = '已过期'
          countdownClass = 'expired'
        } else {
          const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
          const diffDays = Math.floor(diffHours / 24)
          remainingHours = diffHours
          
          if (diffDays >= 1) {
            countdownText = `剩余${diffDays}天`
            if (diffDays <= 3) {
              countdownClass = 'warning'
            }
          } else {
            countdownText = `剩余${diffHours}小时`
            countdownClass = 'urgent'
          }
        }
        
        return {
          ...record,
          countdown_text: countdownText,
          countdown_class: countdownClass,
          remaining_hours: remainingHours
        }
      }
      return record
    })
    
    this.setData({ records })
  },

  deleteRecord(e) {
    const { id } = e.currentTarget.dataset
    
    wx.showModal({
      title: '确认删除',
      content: '删除后无法恢复，是否继续？',
      confirmColor: '#ff3b30',
      success: (res) => {
        if (res.confirm) {
          this.executeDelete(id)
        }
      }
    })
  },

  executeDelete(recordId) {
    wx.showLoading({ title: '删除中...' })
    
    const token = wx.getStorageSync('token')
    const API_BASE_URL = 'https://xn--gmq63iba0780e.com'
    
    wx.request({
      url: `${API_BASE_URL}/api/history/delete`,
      method: 'DELETE',
      data: { record_id: recordId },
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      success: (res) => {
        wx.hideLoading()
        
        if (res.statusCode === 200) {
          wx.showToast({ title: '删除成功', icon: 'success' })
          
          // 从列表中移除
          const records = this.data.records.filter(r => r.id !== recordId)
          this.setData({ records })
        } else {
          wx.showToast({ 
            title: res.data.error || '删除失败', 
            icon: 'none' 
          })
        }
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '删除失败', icon: 'none' })
      }
    })
  },

  formatDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hour = String(d.getHours()).padStart(2, '0')
    const minute = String(d.getMinutes()).padStart(2, '0')
    return `${year}-${month}-${day} ${hour}:${minute}`
  }
})
