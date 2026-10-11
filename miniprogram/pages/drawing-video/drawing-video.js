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

    tGenerating: '正在绘制中...',
    tGeneratingSub: '一笔一画，为您呈现',
    tVideoTitle: '手绘视频',
    tSketchTitle: '素描原图',
    tResultTitle: '原图',
    tCostPrefix: '消耗',
    tHairs: '发丝',
    tRemaining: '剩余',
    tSaveVideo: '保存视频',
    tSaveSketch: '保存图片',
    tSaveResult: '保存原图',
    tGoHome: '返回首页',
    tTapToEnlarge: '点击放大',
    tStyleLabel: '素描风格',
    tStylePencil: '铅笔素描',
    tStyleVivid: '淡彩素描',
    tStyleInk: '水墨风格',
    tStyleAnime: '日式动漫',
    tRegenerate: '重新生成',
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
      this.setData({ error: '缺少素描图，请先完成素描' })
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
      tGenerating: t('drawingVideo.generating') || '正在绘制中...',
      tGeneratingSub: t('drawingVideo.generatingSub') || '一笔一画，为您呈现',
      tVideoTitle: t('drawingVideo.videoTitle') || '手绘视频',
      tSketchTitle: t('drawingVideo.sketchTitle') || '素描原图',
      tResultTitle: t('drawingVideo.resultTitle') || '原图',
      tCostPrefix: t('drawingVideo.costPrefix') || '消耗',
      tHairs: t('drawingVideo.hairs') || '发丝',
      tRemaining: t('drawingVideo.remaining') || '剩余',
      tSaveVideo: t('drawingVideo.saveVideo') || '保存视频',
      tSaveSketch: t('drawingVideo.saveSketch') || '保存图片',
      tSaveResult: t('drawingVideo.saveResult') || '保存原图',
      tGoHome: t('drawingVideo.goHome') || '返回首页',
      tTapToEnlarge: t('drawingVideo.tapToEnlarge') || '点击放大'
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
          error: res.error || '视频生成失败'
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
        error: '视频生成失败，请稍后重试'
      })
    }
  },

  saveVideoToAlbum() {
    const videoUrl = this.data.videoUrl
    if (!videoUrl) return

    wx.showLoading({ title: '保存中...' })

    wx.downloadFile({
      url: videoUrl,
      success: (res) => {
        if (res.statusCode === 200) {
          wx.saveVideoToPhotosAlbum({
            filePath: res.tempFilePath,
            success: () => {
              wx.hideLoading()
              wx.showToast({ title: '保存成功', icon: 'success' })
            },
            fail: (err) => {
              wx.hideLoading()
              if (err.errMsg && err.errMsg.includes('auth deny')) {
                wx.showModal({
                  title: '提示',
                  content: '需要授权保存权限，是否前往设置？',
                  success: (modalRes) => {
                    if (modalRes.confirm) wx.openSetting()
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

  saveSketchToAlbum() {
    const sketchUrl = this.data.sketchUrl
    if (!sketchUrl) return

    let fullUrl = sketchUrl
    if (fullUrl.startsWith('/static/')) {
      fullUrl = API_BASE_URL + fullUrl
    }

    wx.showLoading({ title: '保存中...' })
    wx.getImageInfo({
      src: fullUrl,
      success: (imageRes) => {
        wx.saveImageToPhotosAlbum({
          filePath: imageRes.path,
          success: () => {
            wx.hideLoading()
            wx.showToast({ title: '保存成功', icon: 'success' })
          },
          fail: () => {
            wx.hideLoading()
            wx.showToast({ title: '保存失败', icon: 'none' })
          }
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '图片加载失败', icon: 'none' })
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

    wx.showLoading({ title: '保存中...' })
    wx.getImageInfo({
      src: fullUrl,
      success: (imageRes) => {
        wx.saveImageToPhotosAlbum({
          filePath: imageRes.path,
          success: () => {
            wx.hideLoading()
            wx.showToast({ title: '保存成功', icon: 'success' })
          },
          fail: () => {
            wx.hideLoading()
            wx.showToast({ title: '保存失败', icon: 'none' })
          }
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '图片加载失败', icon: 'none' })
      }
    })
  },

  selectStyle(e) {
    const style = e.currentTarget.dataset.style
    console.log('[selectStyle] 选择风格:', style)
    this.setData({ style })
  },

  regenerateVideo() {
    wx.showModal({
      title: '提示',
      content: `确定要使用"${this._getStyleName(this.data.style)}"风格重新生成视频吗？将再次消耗${this.data.totalCost}发丝。`,
      success: (res) => {
        if (res.confirm) {
          this._startGeneration()
        }
      }
    })
  },

  _getStyleName(style) {
    const styleNames = {
      'pencil': '铅笔素描',
      'vivid': '淡彩素描',
      'ink': '水墨风格',
      'anime': '日式动漫'
    }
    return styleNames[style] || style
  },

  goHome() {
    wx.switchTab({ url: '/pages/index/index' })
  }
})
