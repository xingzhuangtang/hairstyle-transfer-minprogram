// pages/History/history.js
import { getMemberInfo } from '../../api/member.js'
import { getHistoryRecords } from '../../api/hair.js'
import { API_BASE_URL } from '../../utils/constants.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

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
    canvasHeight: 2000,
    // i18n
    // i18n - WXML UI
    tHistoryTitle: '历史记录',
    tHistoryHeaderDescVip: '保留45天，到期自动清理',
    tHistoryHeaderDescNonVip: '开通会员保留 45 天',
    tHistoryOpenVipNotice: '开通陪跑会员',
    tHistoryVipBenefitDesc: '历史记录保留 45 天，随时查看',
    tHistoryEmptyText: '暂无历史记录',
    tHistoryEmptyDesc: '开始使用发型迁移功能后<br/>历史记录将在这里显示',
    tHistoryLoadingText: '加载中...',
    tHistoryNoSketch: '无素描',
    tHistoryFeature1Title: '查看历史',
    tHistoryFeature1Desc: '随时查看发型迁移历史记录',
    tHistoryFeature2Title: '45 天保留',
    tHistoryFeature2Desc: '历史记录保留 45 天',
    tHistoryFeature3Title: '下载保存',
    tHistoryFeature3Desc: '支持下载高清结果图片',
    tHistoryLoadMore: '加载更多',
    tHistoryServiceHairSegment: '发型提取',
    tHistoryServiceFaceMerge: '发型融合',
    tHistoryServiceSketch: '素描转换',
    tHistoryServiceCombined: '一键生成',
    tHistoryServiceFmStep: '融合步骤',
    tHistoryServiceSkStep: '素描步骤',
    tHistoryExpired: '已过期',
    tHistoryDaysRemaining: '剩余{days}天',
    tHistoryHoursRemaining: '剩余{hours}小时',
    tHistoryDefaultServiceType: '发型迁移',
    tHistoryLoadFail: '加载失败',
    tHistoryNoMore: '没有更多了',
    tHistoryRecordExpired: '记录已过期',
    tHistoryPreviewAll: '预览所有图片',
    tHistoryDownloadOriginal: '下载原图',
    tHistoryDownloadSketch: '下载素描',
    tHistorySaveCombined: '保存合并图片',
    tHistoryDeleteRecord: '删除记录',
    tHistoryGeneratingCombined: '生成合并图片中...',
    tHistoryResultLabel: '结果',
    tHistorySketchLabel: '素描',
    tHistoryCombinedSaved: '合并图片已保存到相册',
    tHistorySaveFail: '保存失败',
    tHistoryGenerateFail: '生成失败',
    tHistoryExpiredDownload: '记录已过期，无法下载',
    tHistoryNoImage: '暂无图片',
    tHistoryDownloadImage: '下载图片',
    tHistoryDownloadTip: '点击"预览所有图片"后，长按图片即可保存到相册',
    tHistoryGoPreview: '去预览',
    tHistoryGotIt: '知道了',
    tHistoryPreviewImage: '预览图片',
    tHistoryDownloadToPhone: '下载到手机',
    tHistoryDownloading: '下载中...',
    tHistorySavedToAlbum: '{type}图片已保存到相册',
    tHistoryNeedAlbumAuth: '需要授权访问相册',
    tHistoryGoAuth: '去授权',
    tHistoryDownloadFail: '下载失败',
    tHistoryConfirmDelete: '确认删除',
    tHistoryDeleteContent: '删除后无法恢复，是否继续？',
    tHistoryDeleting: '删除中...',
    tHistoryDeleteSuccess: '删除成功',
    tHistoryDeleteFail: '删除失败'
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'history.title')
    this.loadMemberInfo()
  },

  onShow() {
    this._loadI18n()
    app.setNavTitle(this, 'history.title')
    this.loadMemberInfo()
    this.startCountdownTimer()
  },

  onHide() {
    this.stopCountdownTimer()
  },

  onUnload() {
    this.stopCountdownTimer()
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'history.title')
    })
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      // i18n - WXML UI
      tHistoryTitle: t('history.title'),
      tHistoryHeaderDescVip: t('history.headerDescVip'),
      tHistoryHeaderDescNonVip: t('history.headerDescNonVip'),
      tHistoryOpenVipNotice: t('history.openVipNotice'),
      tHistoryVipBenefitDesc: t('history.vipBenefitDesc'),
      tHistoryEmptyText: t('history.emptyText'),
      tHistoryEmptyDesc: t('history.emptyDesc'),
      tHistoryLoadingText: t('history.loadingText'),
      tHistoryNoSketch: t('history.noSketch'),
      tHistoryFeature1Title: t('history.feature1Title'),
      tHistoryFeature1Desc: t('history.feature1Desc'),
      tHistoryFeature2Title: t('history.feature2Title'),
      tHistoryFeature2Desc: t('history.feature2Desc'),
      tHistoryFeature3Title: t('history.feature3Title'),
      tHistoryFeature3Desc: t('history.feature3Desc'),
      tHistoryLoadMore: t('history.loadMore'),
      tHistoryServiceHairSegment: t('history.serviceHairSegment'),
      tHistoryServiceFaceMerge: t('history.serviceFaceMerge'),
      tHistoryServiceSketch: t('history.serviceSketch'),
      tHistoryServiceCombined: t('history.serviceCombined'),
      tHistoryServiceFmStep: t('history.serviceFmStep'),
      tHistoryServiceSkStep: t('history.serviceSkStep'),
      tHistoryExpired: t('history.expired'),
      tHistoryDaysRemaining: t('history.daysRemaining'),
      tHistoryHoursRemaining: t('history.hoursRemaining'),
      tHistoryDefaultServiceType: t('history.defaultServiceType'),
      tHistoryLoadFail: t('history.loadFail'),
      tHistoryNoMore: t('history.noMore'),
      tHistoryRecordExpired: t('history.recordExpired'),
      tHistoryPreviewAll: t('history.previewAll'),
      tHistoryDownloadOriginal: t('history.downloadOriginal'),
      tHistoryDownloadSketch: t('history.downloadSketch'),
      tHistorySaveCombined: t('history.saveCombined'),
      tHistoryDeleteRecord: t('history.deleteRecord'),
      tHistoryGeneratingCombined: t('history.generatingCombined'),
      tHistoryResultLabel: t('history.resultLabel'),
      tHistorySketchLabel: t('history.sketchLabel'),
      tHistoryCombinedSaved: t('history.combinedSaved'),
      tHistorySaveFail: t('history.saveFail'),
      tHistoryGenerateFail: t('history.generateFail'),
      tHistoryExpiredDownload: t('history.expiredDownload'),
      tHistoryNoImage: t('history.noImage'),
      tHistoryDownloadImage: t('history.downloadImage'),
      tHistoryDownloadTip: t('history.downloadTip'),
      tHistoryGoPreview: t('history.goPreview'),
      tHistoryGotIt: t('history.gotIt'),
      tHistoryPreviewImage: t('history.previewImage'),
      tHistoryDownloadToPhone: t('history.downloadToPhone'),
      tHistoryDownloading: t('history.downloading'),
      tHistorySavedToAlbum: t('history.savedToAlbum'),
      tHistoryNeedAlbumAuth: t('history.needAlbumAuth'),
      tHistoryGoAuth: t('history.goAuth'),
      tHistoryDownloadFail: t('history.downloadFail'),
      tHistoryConfirmDelete: t('history.confirmDelete'),
      tHistoryDeleteContent: t('history.deleteContent'),
      tHistoryDeleting: t('history.deleting'),
      tHistoryDeleteSuccess: t('history.deleteSuccess'),
      tHistoryDeleteFail: t('history.deleteFail')
    })
  },

  _getServiceTypeMap() {
    return {
      hair_segment: this.data.tHistoryServiceHairSegment,
      face_merge: this.data.tHistoryServiceFaceMerge,
      sketch: this.data.tHistoryServiceSketch,
      combined: this.data.tHistoryServiceCombined,
      fm_step: this.data.tHistoryServiceFmStep,
      sk_step: this.data.tHistoryServiceSkStep
    }
  },

  async loadMemberInfo() {
    try {
      const res = await getMemberInfo()
      console.log('会员信息API返回:', res)
      
      if (res.member_level !== undefined) {
        const isVip = res.member_level === 'vip'
        const remainingDays = res.remaining_days || 0

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
        const SERVICE_TYPE_MAP = this._getServiceTypeMap()
        
        const newRecords = res.records.map(record => {
          const resultImage = record.result_image || record.result_url || ''
          const sketchImage = record.sketch_url || ''
          
          let countdownText = ''
          let countdownClass = 'valid'
          let remainingHours = 0
          
          if (record.expire_at) {
            const expireDate = new Date(record.expire_at)
            const now = new Date()
            const diffMs = expireDate - now
            
            if (diffMs <= 0) {
              countdownText = this.data.tHistoryExpired
              countdownClass = 'expired'
            } else {
              const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
              const diffDays = Math.floor(diffHours / 24)
              remainingHours = diffHours
              
              if (diffDays >= 1) {
                countdownText = this.data.tHistoryDaysRemaining.replace('{days}', String(diffDays))
                if (diffDays <= 3) {
                  countdownClass = 'warning'
                }
              } else {
                countdownText = this.data.tHistoryHoursRemaining.replace('{hours}', String(diffHours))
                countdownClass = 'urgent'
              }
            }
          }
          
          return {
            ...record,
            id: record.id,
            result_image: resultImage,
            sketch_image: sketchImage,
            has_sketch: !!sketchImage,
            service_type: record.service_type || 'combined',
            service_type_text: SERVICE_TYPE_MAP[record.service_type] || this.data.tHistoryDefaultServiceType,
            is_expired: record.is_expired || false,
            created_at: this.formatDate(record.created_at),
            countdown_text: countdownText,
            countdown_class: countdownClass,
            remaining_hours: remainingHours
          }
        })

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
      wx.showToast({ title: this.data.tHistoryLoadFail, icon: 'none' })
    }
  },

  loadMore() {
    if (!this.data.hasMore && !this.data.loading) {
      wx.showToast({ title: this.data.tHistoryNoMore, icon: 'none' })
      return
    }
    this.loadHistoryRecords(false)
  },

  viewDetail(e) {
    const { id } = e.currentTarget.dataset
    
    const record = this.data.records.find(r => r.id === id)
    if (!record) return
    
    if (record.is_expired) {
      wx.showToast({ title: this.data.tHistoryRecordExpired, icon: 'none' })
      return
    }

    const menuItems = [this.data.tHistoryPreviewAll]
    if (record.result_image) menuItems.push(this.data.tHistoryDownloadOriginal)
    if (record.sketch_image) menuItems.push(this.data.tHistoryDownloadSketch)
    if (record.result_image && record.sketch_image) menuItems.push(this.data.tHistorySaveCombined)
    menuItems.push(this.data.tHistoryDeleteRecord)

    wx.showActionSheet({
      itemList: menuItems,
      success: (res) => {
        const action = menuItems[res.tapIndex]
        
        if (action === this.data.tHistoryPreviewAll) {
          const imageUrls = []
          if (record.result_image) imageUrls.push(record.result_image)
          if (record.sketch_image) imageUrls.push(record.sketch_image)
          if (imageUrls.length > 0) {
            wx.previewImage({
              urls: imageUrls,
              current: imageUrls[0]
            })
          }
        } else if (action === this.data.tHistoryDownloadOriginal) {
          this.downloadImage(record.result_image, this.data.tHistoryResultLabel)
        } else if (action === this.data.tHistoryDownloadSketch) {
          this.downloadImage(record.sketch_image, this.data.tHistorySketchLabel)
        } else if (action === this.data.tHistorySaveCombined) {
          this.saveCombinedImage(record)
        } else if (action === this.data.tHistoryDeleteRecord) {
          this.deleteRecord({ currentTarget: { dataset: { id } } })
        }
      }
    })
  },

  saveCombinedImage(record) {
    wx.showLoading({ title: this.data.tHistoryGeneratingCombined })

    const images = []
    if (record.result_image) images.push({ url: record.result_image, label: this.data.tHistoryResultLabel })
    if (record.sketch_image) images.push({ url: record.sketch_image, label: this.data.tHistorySketchLabel })

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
                    wx.showToast({ title: this.data.tHistoryCombinedSaved, icon: 'success' })
                  },
                  fail: () => {
                    wx.hideLoading()
                    wx.showToast({ title: this.data.tHistorySaveFail, icon: 'none' })
                  }
                })
              },
              fail: () => {
                wx.hideLoading()
                wx.showToast({ title: this.data.tHistoryGenerateFail, icon: 'none' })
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
      wx.showToast({ title: this.data.tHistoryExpiredDownload, icon: 'none' })
      return
    }

    if (!record.result_image && !record.sketch_image) {
      wx.showToast({ title: this.data.tHistoryNoImage, icon: 'none' })
      return
    }

    wx.showModal({
      title: this.data.tHistoryDownloadImage,
      content: this.data.tHistoryDownloadTip,
      confirmText: this.data.tHistoryGoPreview,
      cancelText: this.data.tHistoryGotIt,
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
      wx.showToast({ title: this.data.tHistoryExpiredDownload, icon: 'none' })
      return
    }

    const imageUrl = type === 'sketch' ? record.sketch_image : record.result_image
    if (!imageUrl) {
      wx.showToast({ title: this.data.tHistoryNoImage, icon: 'none' })
      return
    }

    wx.showActionSheet({
      itemList: [this.data.tHistoryPreviewImage, this.data.tHistoryDownloadToPhone],
      success: (res) => {
        if (res.tapIndex === 0) {
          wx.previewImage({
            urls: [imageUrl],
            current: imageUrl
          })
        } else if (res.tapIndex === 1) {
          this.downloadImage(imageUrl, type === 'sketch' ? this.data.tHistorySketchLabel : this.data.tHistoryResultLabel)
        }
      }
    })
  },

  downloadImage(imageUrl, imageType) {
    wx.showLoading({ title: this.data.tHistoryDownloading })
    
    wx.downloadFile({
      url: imageUrl,
      success: (res) => {
        if (res.statusCode === 200) {
          wx.saveImageToPhotosAlbum({
            filePath: res.tempFilePath,
            success: () => {
              wx.hideLoading()
              wx.showToast({
                title: this.data.tHistorySavedToAlbum.replace('{type}', imageType),
                icon: 'success'
              })
            },
            fail: (err) => {
              wx.hideLoading()
              if (err.errMsg && err.errMsg.includes('auth deny')) {
                wx.showModal({
                  title: app.t('common.tip'),
                  content: this.data.tHistoryNeedAlbumAuth,
                  confirmText: this.data.tHistoryGoAuth,
                  success: (modalRes) => {
                    if (modalRes.confirm) {
                      wx.openSetting()
                    }
                  }
                })
              } else {
                wx.showToast({ title: this.data.tHistorySaveFail, icon: 'none' })
              }
            }
          })
        } else {
          wx.hideLoading()
          wx.showToast({ title: this.data.tHistoryDownloadFail, icon: 'none' })
        }
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: this.data.tHistoryDownloadFail, icon: 'none' })
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
    }, 60 * 60 * 1000)
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
          countdownText = this.data.tHistoryExpired
          countdownClass = 'expired'
        } else {
          const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
          const diffDays = Math.floor(diffHours / 24)
          remainingHours = diffHours
          
          if (diffDays >= 1) {
            countdownText = this.data.tHistoryDaysRemaining.replace('{days}', String(diffDays))
            if (diffDays <= 3) {
              countdownClass = 'warning'
            }
          } else {
            countdownText = this.data.tHistoryHoursRemaining.replace('{hours}', String(diffHours))
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
      title: this.data.tHistoryConfirmDelete,
      content: this.data.tHistoryDeleteContent,
      confirmColor: '#ff3b30',
      success: (res) => {
        if (res.confirm) {
          this.executeDelete(id)
        }
      }
    })
  },

  executeDelete(recordId) {
    wx.showLoading({ title: this.data.tHistoryDeleting })
    
    const token = wx.getStorageSync('token')
    
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
          wx.showToast({ title: this.data.tHistoryDeleteSuccess, icon: 'success' })
          
          const records = this.data.records.filter(r => r.id !== recordId)
          this.setData({ records })
        } else {
          wx.showToast({ 
            title: res.data.error || this.data.tHistoryDeleteFail, 
            icon: 'none' 
          })
        }
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: this.data.tHistoryDeleteFail, icon: 'none' })
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
