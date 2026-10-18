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
    sketchUrlLocal: '',
    resultUrlLocal: '',
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
    resultFullscreen: false,
    resultRevealed: false,
    sketchRevealed: false,
    videoRevealed: false,
    apiCompleted: false,
    transitionVideoLoaded: false,
    revealCells: []
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

        // 只处理相对路径，外部URL（OSS等）保持不变
        if (sketchUrl && sketchUrl.startsWith('/static/')) {
          sketchUrl = API_BASE_URL + sketchUrl
        }

        if (resultUrl && resultUrl.startsWith('/static/')) {
          resultUrl = API_BASE_URL + resultUrl
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

    // 下载初始传入的图片到本地（HTTP 图片微信小程序无法直接显示）
    this._downloadImageToLocal(this.data.sketchUrl, 'sketchUrlLocal')
    if (this.data.resultUrl) {
      this._downloadImageToLocal(this.data.resultUrl, 'resultUrlLocal')
    }

    this._loadUserInfo()
    this._startGeneration()
  },

  onUnload() {
    if (this._animTimer) {
      clearInterval(this._animTimer)
      this._animTimer = null
    }
    if (this._resultTimer) {
      clearTimeout(this._resultTimer)
      this._resultTimer = null
    }
    if (this._sketchTimer) {
      clearTimeout(this._sketchTimer)
      this._sketchTimer = null
    }
    if (this._transitionCheckTimer) {
      clearTimeout(this._transitionCheckTimer)
      this._transitionCheckTimer = null
    }
  },

  onVideoError(e) {
    console.error('[drawing-video] 视频加载失败:', e.detail)
  },

  _checkTransitionComplete() {
    // 只需要 API 完成 + 过渡视频至少播放 5 秒（由调用方定时器保证）
    // 不再等待 videoCanPlay，因为结果视频只在 !generating 时才渲染
    if (this.data.apiCompleted && this.data.generating) {
      console.log('[drawing-video] API 已完成，过渡视频播放足够时间，切换到结果界面')
      this.setData({ generating: false }, () => {
        // 结果界面显示后，启动画笔揭示动画
        this.onResultSectionReady()
      })
    }
  },

  onVideoLoaded(e) {
    console.log('[drawing-video] 视频元数据加载成功:', e.detail)
  },

  onTransitionVideoLoaded(e) {
    console.log('[drawing-video] 过渡视频元数据加载成功:', e.detail)
    this.setData({ transitionVideoLoaded: true })
  },

  // 结果视频区域显示后，启动画笔揭示动画
  onResultSectionReady() {
    const GRID = 10
    const TOTAL_CELLS = GRID * GRID
    const DURATION = 3000 // 总动画时长 3 秒
    const FADE_DURATION = 400 // 每个格子淡出时长

    // 初始化所有格子为不透明（白色遮罩）
    const cells = Array(TOTAL_CELLS).fill(1)
    this.setData({ revealCells: cells, videoRevealed: false })

    // 预计算每个格子的开始时间（对角线波：row + col 越小越早开始）
    const cellStartTimes = []
    for (let i = 0; i < TOTAL_CELLS; i++) {
      const row = Math.floor(i / GRID)
      const col = i % GRID
      const wavePos = (row + col) / ((GRID - 1) * 2) // 0 ~ 1
      cellStartTimes.push(wavePos * (DURATION - FADE_DURATION))
    }

    // 按帧分组：哪些格子在哪个时间点需要更新
    const FRAME_INTERVAL = 50 // 每 50ms 更新一次（20fps，减少 setData 次数）
    const totalFrames = Math.ceil(DURATION / FRAME_INTERVAL)
    const frameBatches = {} // frameIndex -> [cellIndex, ...]

    for (let i = 0; i < TOTAL_CELLS; i++) {
      const startTime = cellStartTimes[i]
      const endTime = startTime + FADE_DURATION
      const startFrame = Math.floor(startTime / FRAME_INTERVAL)
      const endFrame = Math.floor(endTime / FRAME_INTERVAL)

      for (let f = startFrame; f <= endFrame && f < totalFrames; f++) {
        if (!frameBatches[f]) frameBatches[f] = []
        frameBatches[f].push(i)
      }
    }

    let currentFrame = 0
    const animate = () => {
      if (currentFrame >= totalFrames) {
        // 动画完成
        this.setData({ videoRevealed: true })
        return
      }

      const batch = frameBatches[currentFrame]
      if (batch && batch.length > 0) {
        const elapsed = currentFrame * FRAME_INTERVAL
        const newCells = [...this.data.revealCells]
        let changed = false

        for (const idx of batch) {
          const t = cellStartTimes[idx]
          const progress = Math.max(0, Math.min(1, (elapsed - t) / FADE_DURATION))
          const easedProgress = 1 - Math.pow(1 - progress, 3) // ease-out
          const newOpacity = 1 - easedProgress

          if (newCells[idx] !== newOpacity) {
            newCells[idx] = newOpacity
            changed = true
          }
        }

        if (changed) {
          this.setData({ revealCells: newCells })
        }
      }

      currentFrame++
      this._videoRevealTimer = setTimeout(animate, FRAME_INTERVAL)
    }

    animate()
  },

  onImageError(e) {
    console.error('[drawing-video] 图片加载失败:', e.detail, 'src:', e.currentTarget?.dataset?.src)
  },

  _downloadImageToLocal(url, dataKey, callback) {
    console.log(`[drawing-video] 开始下载图片 ${dataKey}:`, url)
    if (!url) {
      console.error('[drawing-video] 图片URL为空:', dataKey)
      if (callback) callback()
      return
    }
    wx.downloadFile({
      url: url,
      success: (res) => {
        console.log(`[drawing-video] 下载响应 ${dataKey}:`, res.statusCode, res.tempFilePath)
        if (res.statusCode === 200) {
          const update = {}
          update[dataKey] = res.tempFilePath
          this.setData(update, () => {
            console.log(`[drawing-video] 图片已设置到data ${dataKey}:`, this.data[dataKey])
            if (callback) callback()
          })
        } else {
          console.error(`[drawing-video] 下载失败，状态码:`, res.statusCode)
          if (callback) callback()
        }
      },
      fail: (err) => {
        console.error(`[drawing-video] 下载失败 ${dataKey}:`, err)
        if (callback) callback()
      }
    })
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
    this.setData({
      generating: true,
      error: '',
      resultRevealed: false,
      sketchRevealed: false,
      videoRevealed: false,
      apiCompleted: false,
      transitionVideoLoaded: false,
      revealCells: Array(100).fill(1)
    })

    console.log('[drawing-video] _startGeneration - style:', this.data.style, 'sketchUrl:', this.data.sketchUrl, 'regenerate:', isRegenerate)

    // 启动过渡视频
    // 直接播放过渡视频，不延迟
    const videoCtx = wx.createVideoContext('transitionVideo', this)
    if (videoCtx) {
      videoCtx.play()
      console.log('[drawing-video] 过渡视频开始播放')
    }

    // 设置过渡视频播放完成检查（至少播放5秒）
    this._transitionCheckTimer = setTimeout(() => {
      this._checkTransitionComplete()
    }, 5000)

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
        const normalizeUrl = (url) => {
          if (!url) return url
          if (url.startsWith('/static/')) {
            return API_BASE_URL + url
          }
          return url
        }

        const updateData = {
          videoReady: true,
          videoUrl: normalizeUrl(res.video_url),
          cost: res.cost,
          remainingHairs: res.remaining_hairs,
          apiCompleted: true
        }

        if (res.sketch_url) {
          const newSketchUrl = normalizeUrl(res.sketch_url)
          updateData.sketchUrl = newSketchUrl
        }

        if (res.result_url) {
          const newResultUrl = normalizeUrl(res.result_url)
          updateData.resultUrl = newResultUrl
        }

        this.setData(updateData)

        // 检查是否应该立即切换到结果界面
        this._checkTransitionComplete()

        // 立即开始下载图片到本地（微信小程序不允许 HTTP 加载图片）
        const sketchToDownload = updateData.sketchUrl || this.data.sketchUrl
        const resultToDownload = updateData.resultUrl || this.data.resultUrl
        
        let sketchDownloaded = false
        let resultDownloaded = false
        
        if (sketchToDownload) {
          this._downloadImageToLocal(sketchToDownload, 'sketchUrlLocal', () => {
            sketchDownloaded = true
          })
        } else {
          sketchDownloaded = true
        }
        
        if (resultToDownload) {
          this._downloadImageToLocal(resultToDownload, 'resultUrlLocal', () => {
            resultDownloaded = true
          })
        } else {
          resultDownloaded = true
        }

        // 配合视频播放节奏：第10秒显示原图，第20秒显示素描
        // 需要同时满足：定时器到达 + 图片已下载完成
        if (this._resultTimer) {
          clearTimeout(this._resultTimer)
          this._resultTimer = null
        }
        if (this._sketchTimer) {
          clearTimeout(this._sketchTimer)
          this._sketchTimer = null
        }

        // 第10秒显示原图（带画笔揭示效果）
        this._resultTimer = setTimeout(() => {
          console.log('[drawing-video] 第10秒定时器触发, resultDownloaded:', resultDownloaded, 'resultUrlLocal:', this.data.resultUrlLocal)
          const tryShowResult = () => {
            if (resultDownloaded) {
              this.setData({ showResult: true }, () => {
                console.log('[drawing-video] showResult 已设置为 true')
                // 延迟触发布画揭示动画
                setTimeout(() => {
                  this.setData({ resultRevealed: true })
                }, 100)
              })
            } else {
              setTimeout(tryShowResult, 500)
            }
          }
          tryShowResult()
        }, 10000)

        // 第20秒显示素描（带画笔揭示效果）
        this._sketchTimer = setTimeout(() => {
          console.log('[drawing-video] 第20秒定时器触发, sketchDownloaded:', sketchDownloaded, 'sketchUrlLocal:', this.data.sketchUrlLocal)
          const tryShowSketch = () => {
            if (sketchDownloaded) {
              this.setData({ showSketch: true }, () => {
                console.log('[drawing-video] showSketch 已设置为 true, sketchUrlLocal:', this.data.sketchUrlLocal)
                // 延迟触发布画揭示动画
                setTimeout(() => {
                  this.setData({ sketchRevealed: true })
                }, 100)
              })
            } else {
              setTimeout(tryShowSketch, 500)
            }
          }
          tryShowSketch()
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

    // OSS 域名不在小程序白名单中，需通过服务器代理下载
    let downloadUrl = videoUrl
    const header = {}
    if (!videoUrl.startsWith('/static/') && !videoUrl.startsWith(API_BASE_URL)) {
      downloadUrl = `${API_BASE_URL}/api/proxy/resource?url=${encodeURIComponent(videoUrl)}`
      const { getToken } = require('../../utils/storage.js')
      const token = getToken()
      if (token) {
        header['Authorization'] = `Bearer ${token}`
      }
    }

    wx.downloadFile({
      url: downloadUrl,
      header: header,
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
