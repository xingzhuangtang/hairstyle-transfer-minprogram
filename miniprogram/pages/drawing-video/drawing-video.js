// pages/drawing-video/drawing-video.js
import { generateDrawingVideo } from '../../api/hair.js'
import { refreshUserInfo } from '../../utils/auth.js'
import { API_BASE_URL, PRICING } from '../../utils/constants.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    sketchUrl: '',
    resultUrl: '',
    style: 'pencil',
    cost: 0,
    totalCost: 0,
    generating: false,
    videoReady: false,
    showSketch: false,
    showResult: false,
    videoUrl: '',
    remainingHairs: 0,
    error: '',
    transitionVideoUrl: `${API_BASE_URL}/static/assets/drawing-transition.mp4`,

    videoFullscreen: false,
    sketchFullscreen: false,
    resultFullscreen: false
  },

  _animTimer: null,

  onLoad(options) {
    this._loadI18n()
    this._setupLocaleListener()

    if (options.data) {
      try {
        const data = JSON.parse(decodeURIComponent(options.data))
        let sketchUrl = data.sketchUrl || ''
        let resultUrl = data.resultUrl || ''

        // 统一转换为当前 API_BASE_URL（处理相对路径和旧的内网IP地址）
        if (sketchUrl) {
          if (sketchUrl.startsWith('http')) {
            const pathStart = sketchUrl.indexOf('/', sketchUrl.indexOf('//') + 2)
            if (pathStart !== -1) {
              sketchUrl = API_BASE_URL + sketchUrl.substring(pathStart)
            }
          } else if (sketchUrl.startsWith('/')) {
            sketchUrl = API_BASE_URL + sketchUrl
          }
        }

        if (resultUrl) {
          if (resultUrl.startsWith('http')) {
            const pathStart = resultUrl.indexOf('/', resultUrl.indexOf('//') + 2)
            if (pathStart !== -1) {
              resultUrl = API_BASE_URL + resultUrl.substring(pathStart)
            }
          } else if (resultUrl.startsWith('/')) {
            resultUrl = API_BASE_URL + resultUrl
          }
        }

        const isPremium = app.globalData && app.globalData.userInfo && app.globalData.userInfo.member_level === 'vip'
        const drawingVideoCost = data.cost || (isPremium ? PRICING.vip.drawingVideo : PRICING.normal.drawingVideo)
        const combinedCost = isPremium ? PRICING.vip.combined : PRICING.normal.combined
        const totalCost = combinedCost + drawingVideoCost

        this.setData({
          sketchUrl: sketchUrl,
          resultUrl: resultUrl,
          style: data.style || 'vivid',
          cost: drawingVideoCost,
          totalCost: totalCost
        })
      } catch (e) {
        console.error('解析参数失败:', e)
      }
    }

    if (!this.data.sketchUrl) {
      this.setData({ error: this.data.tErrorNoSketch })
      return
    }

    this._loadUserInfo()
    this._startGeneration()
  },

  onUnload() {
    if (this._animTimer) {
      clearInterval(this._animTimer)
      this._animTimer = null
    }
    if (this._sketchTimer) {
      clearTimeout(this._sketchTimer)
      this._sketchTimer = null
    }
    if (this._resultTimer) {
      clearTimeout(this._resultTimer)
      this._resultTimer = null
    }
  },

  onVideoError(e) {
    console.error('[drawing-video] 视频加载失败:', e.detail)
  },

  onVideoLoaded(e) {
    console.log('[drawing-video] 视频元数据加载成功:', e.detail)
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tGenerating: t('drawingVideo.generating'),
      tGeneratingSub: t('drawingVideo.generatingSub'),
      tVideoTitle: t('drawingVideo.videoTitle'),
      tSketchTitle: t('drawingVideo.sketchTitle'),
      tResultTitle: t('drawingVideo.resultTitle'),
      tCostPrefix: t('drawingVideo.costPrefix'),
      tHairs: t('drawingVideo.hairs'),
      tRemaining: t('drawingVideo.remaining'),
      tSaveVideo: t('drawingVideo.saveVideo'),
      tSaveSketch: t('drawingVideo.saveSketch'),
      tSaveResult: t('drawingVideo.saveResult'),
      tGoHome: t('drawingVideo.goHome'),
      tTapToEnlarge: t('drawingVideo.tapToEnlarge'),
      tStyleLabel: t('drawingVideo.styleLabel'),
      tStylePencil: t('drawingVideo.stylePencil'),
      tStyleVivid: t('drawingVideo.styleVivid'),
      tStyleInk: t('drawingVideo.styleInk'),
      tStyleAnime: t('drawingVideo.styleAnime'),
      tRegenerate: t('drawingVideo.regenerate'),
      tSaving: t('drawingVideo.saving'),
      tSaveSuccess: t('drawingVideo.saveSuccess'),
      tSaveFail: t('drawingVideo.saveFail'),
      tDownloadFail: t('drawingVideo.downloadFail'),
      tImageLoadFail: t('drawingVideo.imageLoadFail'),
      tNeedPermission: t('drawingVideo.needPermission'),
      tErrorNoSketch: t('drawingVideo.errorNoSketch'),
      tErrorGenerateFail: t('drawingVideo.errorGenerateFail'),
      tTip: t('common.tip')
    })
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
    })
  },

  async _loadUserInfo() {
    try {
      const res = await refreshUserInfo()
      if (res.success) {
        this.setData({
          remainingHairs: (res.user.scissor_hairs || 0) + (res.user.comb_hairs || 0)
        })
      }
    } catch (e) {
      console.error('加载用户信息失败:', e)
    }
  },

  async _startGeneration() {
    const isRegenerate = this.data.videoReady || !!this.data.videoUrl
    this.setData({ generating: true, error: '' })

    console.log('[drawing-video] _startGeneration - style:', this.data.style, 'sketchUrl:', this.data.sketchUrl, 'regenerate:', isRegenerate)

    setTimeout(() => {
      const videoCtx = wx.createVideoContext('transitionVideo', this)
      if (videoCtx) {
        videoCtx.play()
        console.log('[drawing-video] 过渡视频开始播放')
      }
    }, 300)

    try {
      const res = await generateDrawingVideo({
        style: this.data.style,
        sketch_url: this.data.sketchUrl,
        mode: 'programmatic',
        regenerate_sketch: isRegenerate
      })

      if (this._animTimer) {
        clearInterval(this._animTimer)
        this._animTimer = null
      }

      if (res.success) {
        let videoUrl = res.video_url
        if (videoUrl && videoUrl.startsWith('/static/')) {
          videoUrl = API_BASE_URL + videoUrl
        }

        const updateData = {
          generating: false,
          videoReady: true,
          showSketch: false,
          showResult: false,
          videoUrl: videoUrl,
          cost: res.cost,
          remainingHairs: res.remaining_hairs
        }

        if (res.sketch_url) {
          let newSketchUrl = res.sketch_url
          if (newSketchUrl.startsWith('/static/')) {
            newSketchUrl = API_BASE_URL + newSketchUrl
          } else if (newSketchUrl.startsWith('http')) {
            const pathStart = newSketchUrl.indexOf('/', newSketchUrl.indexOf('//') + 2)
            if (pathStart !== -1) {
              newSketchUrl = API_BASE_URL + newSketchUrl.substring(pathStart)
            }
          }
          updateData.sketchUrl = newSketchUrl
          console.log('[drawing-video] 素描已更新:', newSketchUrl)
        }

        this.setData(updateData)

        // 清除旧定时器
        if (this._resultTimer) {
          clearTimeout(this._resultTimer)
          this._resultTimer = null
        }
        if (this._sketchTimer) {
          clearTimeout(this._sketchTimer)
          this._sketchTimer = null
        }

        // 10 秒后显示原图
        if (this.data.resultUrl) {
          this._resultTimer = setTimeout(() => {
            this.setData({ showResult: true })
          }, 10000)
        }

        // 20 秒后显示素描图片
        this._sketchTimer = setTimeout(() => {
          this.setData({ showSketch: true })
        }, 20000)
      } else {
        this.setData({
          generating: false,
          error: res.error || this.data.tErrorGenerateFail
        })
      }
    } catch (e) {
      if (this._animTimer) {
        clearInterval(this._animTimer)
        this._animTimer = null
      }
      console.error('生成视频失败:', e)
      this.setData({
        generating: false,
        error: this.data.tErrorGenerateFail
      })
    }
  },

  saveVideoToAlbum() {
    const videoUrl = this.data.videoUrl
    if (!videoUrl) return

    wx.showLoading({ title: this.data.tSaving })

    wx.downloadFile({
      url: videoUrl,
      success: (res) => {
        if (res.statusCode === 200) {
          wx.saveVideoToPhotosAlbum({
            filePath: res.tempFilePath,
            success: () => {
              wx.hideLoading()
              wx.showToast({ title: this.data.tSaveSuccess, icon: 'success' })
            },
            fail: (err) => {
              wx.hideLoading()
              if (err.errMsg && err.errMsg.includes('auth deny')) {
                wx.showModal({
                  title: this.data.tTip,
                  content: this.data.tNeedPermission,
                  success: (modalRes) => {
                    if (modalRes.confirm) wx.openSetting()
                  }
                })
              } else {
                wx.showToast({ title: this.data.tSaveFail, icon: 'none' })
              }
            }
          })
        } else {
          wx.hideLoading()
          wx.showToast({ title: this.data.tDownloadFail, icon: 'none' })
        }
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: this.data.tDownloadFail, icon: 'none' })
      }
    })
  },

  saveSketchToAlbum() {
    const sketchUrl = this.data.sketchUrl
    if (!sketchUrl) return

    let fullUrl = sketchUrl
    if (fullUrl.startsWith('/static/')) {
      fullUrl = API_BASE_URL + fullUrl
    }

    wx.showLoading({ title: this.data.tSaving })
    wx.getImageInfo({
      src: fullUrl,
      success: (imageRes) => {
        wx.saveImageToPhotosAlbum({
          filePath: imageRes.path,
          success: () => {
            wx.hideLoading()
            wx.showToast({ title: this.data.tSaveSuccess, icon: 'success' })
          },
          fail: () => {
            wx.hideLoading()
            wx.showToast({ title: this.data.tSaveFail, icon: 'none' })
          }
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: this.data.tImageLoadFail, icon: 'none' })
      }
    })
  },

  openFullscreenVideo() {
    this.setData({ videoFullscreen: true })
  },

  closeFullscreenVideo() {
    this.setData({ videoFullscreen: false })
  },

  openFullscreenSketch() {
    this.setData({ sketchFullscreen: true })
  },

  closeFullscreenSketch() {
    this.setData({ sketchFullscreen: false })
  },

  openFullscreenResult() {
    this.setData({ resultFullscreen: true })
  },

  closeFullscreenResult() {
    this.setData({ resultFullscreen: false })
  },

  saveResultToAlbum() {
    const resultUrl = this.data.resultUrl
    if (!resultUrl) return

    let fullUrl = resultUrl
    if (fullUrl.startsWith('/static/')) {
      fullUrl = API_BASE_URL + fullUrl
    }

    wx.showLoading({ title: this.data.tSaving })
    wx.getImageInfo({
      src: fullUrl,
      success: (imageRes) => {
        wx.saveImageToPhotosAlbum({
          filePath: imageRes.path,
          success: () => {
            wx.hideLoading()
            wx.showToast({ title: this.data.tSaveSuccess, icon: 'success' })
          },
          fail: () => {
            wx.hideLoading()
            wx.showToast({ title: this.data.tSaveFail, icon: 'none' })
          }
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: this.data.tImageLoadFail, icon: 'none' })
      }
    })
  },

  selectStyle(e) {
    const style = e.currentTarget.dataset.style
    console.log('[selectStyle] 选择风格:', style)
    this.setData({ style })
  },

  regenerateVideo() {
    const styleName = this._getStyleName(this.data.style)
    const content = app.t('drawingVideo.regenerateConfirm', {
      style: styleName,
      cost: this.data.totalCost
    })
    wx.showModal({
      title: this.data.tTip,
      content: content,
      success: (res) => {
        if (res.confirm) {
          this._startGeneration()
        }
      }
    })
  },

  _getStyleName(style) {
    const styleNames = {
      'pencil': app.t('drawingVideo.stylePencil'),
      'vivid': app.t('drawingVideo.styleVivid'),
      'ink': app.t('drawingVideo.styleInk'),
      'anime': app.t('drawingVideo.styleAnime')
    }
    return styleNames[style] || style
  },

  goHome() {
    wx.switchTab({ url: '/pages/index/index' })
  }
})
