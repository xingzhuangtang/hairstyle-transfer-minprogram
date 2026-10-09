// pages/drawing-video/drawing-video.js
import { generateDrawingVideo } from '../../api/hair.js'
import { refreshUserInfo } from '../../utils/auth.js'
import { API_BASE_URL } from '../../utils/constants.js'
import { onLocaleChange } from '../../utils/i18n.js'

const app = getApp()

Page({
  data: {
    sketchUrl: '',
    style: 'pencil',
    cost: 0,
    generating: false,
    videoReady: false,
    showSketch: false,
    videoUrl: '',
    remainingHairs: 0,
    error: '',

    tGenerating: '正在绘制中...',
    tGeneratingSub: '一笔一画，为您呈现',
    tVideoTitle: '手绘视频',
    tSketchTitle: '素描原图',
    tCostPrefix: '消耗',
    tHairs: '发丝',
    tRemaining: '剩余',
    tSaveVideo: '保存视频',
    tSaveSketch: '保存图片',
    tGoHome: '返回首页',
    tTapToEnlarge: '点击放大',
    tStyleLabel: '素描风格',
    tStylePencil: '铅笔素描',
    tStyleVivid: '淡彩素描',
    tStyleInk: '水墨风格',
    tStyleAnime: '日式动漫',
    tRegenerate: '重新生成',
    videoFullscreen: false,
    sketchFullscreen: false
  },

  _animTimer: null,

  onLoad(options) {
    this._loadI18n()
    this._setupLocaleListener()

    if (options.data) {
      try {
        const data = JSON.parse(decodeURIComponent(options.data))
        let sketchUrl = data.sketchUrl || ''

        // 统一转换为当前 API_BASE_URL（处理相对路径和旧的内网IP地址）
        if (sketchUrl) {
          if (sketchUrl.startsWith('http')) {
            // 完整URL，提取路径部分
            const pathStart = sketchUrl.indexOf('/', sketchUrl.indexOf('//') + 2)
            if (pathStart !== -1) {
              sketchUrl = API_BASE_URL + sketchUrl.substring(pathStart)
            }
          } else if (sketchUrl.startsWith('/')) {
            // 相对路径，拼接 API_BASE_URL
            sketchUrl = API_BASE_URL + sketchUrl
          }
        }

        this.setData({
          sketchUrl: sketchUrl,
          style: data.style || 'vivid',
          cost: data.cost || 50
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
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tGenerating: t('drawingVideo.generating') || '正在绘制中...',
      tGeneratingSub: t('drawingVideo.generatingSub') || '一笔一画，为您呈现',
      tVideoTitle: t('drawingVideo.videoTitle') || '手绘视频',
      tSketchTitle: t('drawingVideo.sketchTitle') || '素描原图',
      tCostPrefix: t('drawingVideo.costPrefix') || '消耗',
      tHairs: t('drawingVideo.hairs') || '发丝',
      tRemaining: t('drawingVideo.remaining') || '剩余',
      tSaveVideo: t('drawingVideo.saveVideo') || '保存视频',
      tSaveSketch: t('drawingVideo.saveSketch') || '保存图片',
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
    this.setData({ generating: true, error: '' })
    this._playRevealAnimation()

    try {
      const res = await generateDrawingVideo({
        style: this.data.style,
        sketch_url: this.data.sketchUrl,
        mode: 'programmatic'
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

        this.setData({
          generating: false,
          videoReady: true,
          showSketch: false,
          videoUrl: videoUrl,
          cost: res.cost,
          remainingHairs: res.remaining_hairs
        })

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

  _playRevealAnimation() {
    const query = wx.createSelectorQuery()
    query.select('#revealCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res || !res[0]) return

        const canvas = res[0].node
        const ctx = canvas.getContext('2d')
        const dpr = wx.getWindowInfo().pixelRatio
        canvas.width = res[0].width * dpr
        canvas.height = res[0].height * dpr
        ctx.scale(dpr, dpr)

        const width = res[0].width
        const height = res[0].height
        const style = this.data.style

        const img = canvas.createImage()
        img.onload = () => {
          const imgW = img.width
          const imgH = img.height
          const scale = Math.min(width / imgW, height / imgH)
          const drawW = imgW * scale
          const drawH = imgH * scale
          const offsetX = (width - drawW) / 2
          const offsetY = (height - drawH) / 2

          let progress = 0
          const totalDuration = 5000
          const interval = 1000 / 24
          const steps = totalDuration / interval

          this._animTimer = setInterval(() => {
            progress += 1 / steps
            if (progress > 1) progress = 0

            ctx.clearRect(0, 0, width, height)

            if (style === 'pencil') {
              this._drawPencilReveal(ctx, img, offsetX, offsetY, drawW, drawH, progress)
            } else if (style === 'ink') {
              this._drawInkReveal(ctx, img, offsetX, offsetY, drawW, drawH, progress)
            } else if (style === 'anime') {
              this._drawAnimeReveal(ctx, img, offsetX, offsetY, drawW, drawH, progress)
            } else {
              this._drawVividReveal(ctx, img, offsetX, offsetY, drawW, drawH, progress)
            }
          }, interval)
        }
        img.src = this.data.sketchUrl
      })
  },

  _drawPencilReveal(ctx, img, x, y, w, h, progress) {
    ctx.save()
    ctx.beginPath()
    const clipY = y + h * progress
    ctx.rect(x, y, w, clipY - y)
    ctx.clip()
    ctx.drawImage(img, x, y, w, h)
    ctx.restore()

    if (progress < 1) {
      ctx.save()
      ctx.strokeStyle = '#333'
      ctx.lineWidth = 2
      ctx.beginPath()
      const lineY = clipY
      for (let lx = x; lx < x + w; lx += 6) {
        ctx.moveTo(lx, lineY)
        ctx.lineTo(lx + 3, lineY - 2)
      }
      ctx.stroke()
      ctx.restore()
    }
  },

  _drawInkReveal(ctx, img, x, y, w, h, progress) {
    const numDrops = 8
    ctx.save()

    for (let i = 0; i < numDrops; i++) {
      const cx = x + w * (0.15 + 0.7 * ((i * 0.618) % 1))
      const cy = y + h * (0.15 + 0.7 * ((i * 0.414 + 0.3) % 1))
      const maxR = Math.max(w, h) * 0.4 * (0.7 + 0.3 * ((i * 0.3) % 1))
      const r = maxR * progress

      if (r > 0) {
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.clip()
      }
    }

    ctx.drawImage(img, x, y, w, h)
    ctx.restore()
  },

  _drawAnimeReveal(ctx, img, x, y, w, h, progress) {
    ctx.save()
    if (progress < 0.6) {
      const lineProgress = progress / 0.6
      const clipH = h * lineProgress
      ctx.beginPath()
      ctx.rect(x, y, w, clipH)
      ctx.clip()
      ctx.drawImage(img, x, y, w, h)

      ctx.strokeStyle = '#000'
      ctx.lineWidth = 1.5
      const edgeY = y + clipH
      ctx.beginPath()
      ctx.moveTo(x, edgeY)
      ctx.lineTo(x + w, edgeY)
      ctx.stroke()
    } else {
      ctx.drawImage(img, x, y, w, h)
    }
    ctx.restore()
  },

  _drawVividReveal(ctx, img, x, y, w, h, progress) {
    const numBlobs = 10
    ctx.save()

    for (let i = 0; i < numBlobs; i++) {
      const cx = x + w * (0.1 + 0.8 * ((i * 0.5 + 0.2) % 1))
      const cy = y + h * (0.1 + 0.8 * ((i * 0.37 + 0.1) % 1))
      const maxR = Math.max(w, h) * 0.35
      const r = maxR * progress * (0.6 + 0.4 * ((i * 0.25) % 1))

      if (r > 0) {
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.clip()
      }
    }

    ctx.drawImage(img, x, y, w, h)
    ctx.restore()
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

  selectStyle(e) {
    const style = e.currentTarget.dataset.style
    this.setData({ style })
  },

  regenerateVideo() {
    wx.showModal({
      title: '提示',
      content: `确定要使用"${this._getStyleName(this.data.style)}"风格重新生成视频吗？将再次消耗${this.data.cost}发丝。`,
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
