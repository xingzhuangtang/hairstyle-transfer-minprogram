// pages/History/history.js
import { getMemberInfo } from '../../api/member.js'
import { getHistoryRecords } from '../../api/hair.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

// 服务类型映射 key
const SERVICE_TYPE_KEYS = {
  hair_segment: 'history.serviceHairSegment',
  face_merge: 'history.serviceFaceMerge',
  sketch: 'history.serviceSketch',
  combined: 'history.serviceCombined',
  fm_step: 'history.serviceFmStep',
  sk_step: 'history.serviceSkStep'
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
    // i18n
    tHistoryTitle: '',
    tHistoryRemainingDays: '',
    tHistoryMemberOnly: '',
    tHistoryOpenMember: '',
    tHistoryMemberBenefit: '',
    tHistoryEmpty: '',
    tHistoryEmptyTip: '',
    tHistoryLoadingText: '',
    tHistoryNoSketch: '',
    tHistoryResult: '',
    tHistorySketch: '',
    tHistoryLoadMore: '',
    tHistoryFeature1Title: '',
    tHistoryFeature1Desc: '',
    tHistoryFeature2Title: '',
    tHistoryFeature2Desc: '',
    tHistoryFeature3Title: '',
    tHistoryFeature3Desc: '',
    tHistoryPreviewAll: '',
    tHistoryDownloadOriginal: '',
    tHistoryDownloadSketch: '',
    tHistorySaveCombined: '',
    tHistoryDeleteRecord: '',
    tHistoryRecordExpired: '',
    tHistoryRecordExpiredDownload: '',
    tHistoryNoImage: '',
    tHistoryDownloadTip: '',
    tHistoryGoPreview: '',
    tHistoryGotIt: '',
    tHistoryPreviewImage: '',
    tHistoryDownloadToPhone: '',
    tHistoryDownloading: '',
    tHistoryAlbumSaved: '',
    tHistoryNeedAlbumPermission: '',
    tHistoryGoAuth: '',
    tHistorySaveFail: '',
    tHistoryDownloadFail: '',
    tHistoryConfirmDelete: '',
    tHistoryDeleteContent: '',
    tHistoryDeleteSuccess: '',
    tHistoryDeleteFail: '',
    tHistoryGeneratingCombined: '',
    tHistoryCombinedSaved: '',
    tHistoryGenerateFail: '',
    tHistoryOriginalLabel: '',
    tHistorySketchLabel: '',
    tHistoryNoMoreRecords: '',
    tHistoryLoadFail: '',
    tHistoryRemainingDaysTpl: '',
    tHistoryDaysRemaining: '',
    tHistoryHoursRemaining: ''
  },

  _serviceTypeMap: {},

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

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tHistoryTitle: t('history.title'),
      tHistoryRemainingDays: t('history.remainingDays'),
      tHistoryMemberOnly: t('history.memberOnly'),
      tHistoryOpenMember: t('history.openMember'),
      tHistoryMemberBenefit: t('history.memberBenefit'),
      tHistoryEmpty: t('history.empty'),
      tHistoryEmptyTip: t('history.emptyTip'),
      tHistoryLoadingText: t('history.loadingText'),
      tHistoryNoSketch: t('history.noSketch'),
      tHistoryResult: t('history.result'),
      tHistorySketch: t('history.sketch'),
      tHistoryLoadMore: t('history.loadMore'),
      tHistoryFeature1Title: t('history.feature1Title'),
      tHistoryFeature1Desc: t('history.feature1Desc'),
      tHistoryFeature2Title: t('history.feature2Title'),
      tHistoryFeature2Desc: t('history.feature2Desc'),
      tHistoryFeature3Title: t('history.feature3Title'),
      tHistoryFeature3Desc: t('history.feature3Desc'),
      tHistoryPreviewAll: t('history.previewAll'),
      tHistoryDownloadOriginal: t('history.downloadOriginal'),
      tHistoryDownloadSketch: t('history.downloadSketch'),
      tHistorySaveCombined: t('history.saveCombined'),
      tHistoryDeleteRecord: t('history.deleteRecord'),
      tHistoryRecordExpired: t('history.recordExpired'),
      tHistoryRecordExpiredDownload: t('history.recordExpiredDownload'),
      tHistoryNoImage: t('history.noImage'),
      tHistoryDownloadTip: t('history.downloadTip'),
      tHistoryGoPreview: t('history.goPreview'),
      tHistoryGotIt: t('history.gotIt'),
      tHistoryPreviewImage: t('history.previewImage'),
      tHistoryDownloadToPhone: t('history.downloadToPhone'),
      tHistoryDownloading: t('history.downloading'),
      tHistoryAlbumSaved: t('history.albumSaved'),
      tHistoryNeedAlbumPermission: t('history.needAlbumPermission'),
      tHistoryGoAuth: t('history.goAuth'),
      tHistorySaveFail: t('history.saveFail'),
      tHistoryDownloadFail: t('history.downloadFail'),
      tHistoryConfirmDelete: t('history.confirmDelete'),
      tHistoryDeleteContent: t('history.deleteContent'),
      tHistoryDeleteSuccess: t('history.deleteSuccess'),
      tHistoryDeleteFail: t('history.deleteFail'),
      tHistoryGeneratingCombined: t('history.generatingCombined'),
      tHistoryCombinedSaved: t('history.combinedSaved'),
      tHistoryGenerateFail: t('history.generateFail'),
      tHistoryOriginalLabel: t('history.originalLabel'),
      tHistorySketchLabel: t('history.sketchLabel'),
      tHistoryNoMoreRecords: t('history.noMoreRecords'),
      tHistoryLoadFail: t('history.loadFail'),
      tHistoryRemainingDaysTpl: t('history.remainingDays'),
      tHistoryDaysRemaining: t('history.daysRemaining'),
      tHistoryHoursRemaining: t('history.hoursRemaining')
    })
    // 更新服务类型映射
    this._serviceTypeMap = {}
    for (const [key, i18nKey] of Object.entries(SERVICE_TYPE_KEYS)) {
      this._serviceTypeMap[key] = t(i18nKey)
    }
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'history.title')
    })
  },

  async loadMemberInfo() {
    try {
      const res = await getMemberInfo()
      console.log('会员信息API返回:', res)

      if (res.member_level !== undefined) {
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

          let countdownText = ''
          let countdownClass = 'valid'
          let remainingHours = 0

          if (record.expire_at) {
            const expireDate = new Date(record.expire_at)
            const now = new Date()
            const diffMs = expireDate - now

            if (diffMs <= 0) {
              countdownText = this.data.tHistoryRecordExpired
              countdownClass = 'expired'
            } else {
              const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
              const diffDays = Math.floor(diffHours / 24)
              remainingHours = diffHours

              if (diffDays >= 1) {
                countdownText = this.data.tHistoryDaysRemaining.replace('{d}', String(diffDays))
                if (diffDays <= 3) {
                  countdownClass = 'warning'
                }
              } else {
                countdownText = this.data.tHistoryHoursRemaining.replace('{h}', String(diffHours))
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
            service_type_text: this._serviceTypeMap[record.service_type] || this._serviceTypeMap['combined'] || '',
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
      wx.showToast({ title: this.data.tHistoryLoadFail, icon: 'none' })
    }
  },

  loadMore() {
    if (!this.data.hasMore && !this.data.loading) {
      wx.showToast({ title: this.data.tHistoryNoMoreRecords, icon: 'none' })
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
          this.downloadImage(record.result_image, this.data.tHistoryOriginalLabel)
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

    const ctx = wx.createCanvasContext('combinedCanvas', this)

    ctx.setFillStyle('#ffffff')
    ctx.fillRect(0, 0, 800, 1600)

    let loadedCount = 0
    const totalImages = (record.result_image ? 1 : 0) + (record.sketch_image ? 1 : 0)

    const onLoadComplete = () => {
      loadedCount++
      if (loadedCount === totalImages) {
        ctx.draw(false, () => {
          setTimeout(() => {
            wx.canvasToTempFilePath({
              canvasId: 'combinedCanvas',
              width: 800,
              height: 1600,
              destWidth: 1600,
              destHeight: 3200,
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
          }, 1000)
        })
      }
    }

    if (record.result_image) {
      wx.downloadFile({
        url: record.result_image,
        success: (res) => {
          if (res.statusCode === 200) {
            ctx.drawImage(res.tempFilePath, 0, 0, 800, 800)
            ctx.setFillStyle('rgba(0, 0, 0, 0.6)')
            ctx.fillRect(10, 760, 100, 30)
            ctx.setFillStyle('#ffffff')
            ctx.setFontSize(18)
            ctx.fillText(this.data.tHistoryOriginalLabel, 30, 782)
          }
          onLoadComplete()
        },
        fail: () => onLoadComplete()
      })
    } else {
      onLoadComplete()
    }

    if (record.sketch_image) {
      wx.downloadFile({
        url: record.sketch_image,
        success: (res) => {
          if (res.statusCode === 200) {
            ctx.drawImage(res.tempFilePath, 0, 800, 800, 800)
            ctx.setFillStyle('rgba(0, 0, 0, 0.6)')
            ctx.fillRect(10, 1560, 100, 30)
            ctx.setFillStyle('#ffffff')
            ctx.setFontSize(18)
            ctx.fillText(this.data.tHistorySketchLabel, 30, 1582)
          }
          onLoadComplete()
        },
        fail: () => onLoadComplete()
      })
    } else {
      onLoadComplete()
    }
  },

  downloadCombinedImage(e) {
    const { id } = e.currentTarget.dataset
    const record = this.data.records.find(r => r.id === id)
    if (!record) return

    if (record.is_expired) {
      wx.showToast({ title: this.data.tHistoryRecordExpiredDownload, icon: 'none' })
      return
    }

    if (!record.result_image && !record.sketch_image) {
      wx.showToast({ title: this.data.tHistoryNoImage, icon: 'none' })
      return
    }

    wx.showModal({
      title: this.data.tHistoryDownloadToPhone,
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
      wx.showToast({ title: this.data.tHistoryRecordExpiredDownload, icon: 'none' })
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
          this.downloadImage(imageUrl, type === 'sketch' ? this.data.tHistorySketchLabel : this.data.tHistoryResult)
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
              wx.showToast({ title: `${imageType}${this.data.tHistoryAlbumSaved}`, icon: 'success' })
            },
            fail: (err) => {
              wx.hideLoading()
              if (err.errMsg && err.errMsg.includes('auth deny')) {
                wx.showModal({
                  title: this.data.tHistoryGotIt,
                  content: this.data.tHistoryNeedAlbumPermission,
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
          countdownText = this.data.tHistoryRecordExpired
          countdownClass = 'expired'
        } else {
          const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
          const diffDays = Math.floor(diffHours / 24)
          remainingHours = diffHours

          if (diffDays >= 1) {
            countdownText = this.data.tHistoryDaysRemaining.replace('{d}', String(diffDays))
            if (diffDays <= 3) {
              countdownClass = 'warning'
            }
          } else {
            countdownText = this.data.tHistoryHoursRemaining.replace('{h}', String(diffHours))
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
    wx.showLoading({ title: this.data.tHistoryDeleteRecord })

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
