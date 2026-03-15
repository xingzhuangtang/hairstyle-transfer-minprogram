// pages/result/result.js
import { getUserInfo, checkBalance } from '../../api/user.js'
import { refreshUserInfo } from '../../utils/auth.js'
import { PRICING } from '../../utils/constants.js'

Page({
  data: {
    resultUrl: '',
    originalUrl: '',     // 原图 URL（素描模式）
    rawResultUrl: '',    // 原始结果 URL（用于保存）
    rawOriginalUrl: '',  // 原始原图 URL（用于保存）
    cost: 0,
    mode: 'normal',     // 显示模式：normal/sketch
    showComparison: false,  // 是否显示对比
    combCost: 0,
    scissorCost: 0,
    remainingHairs: 0,
    showSaveSuccess: false
  },

  onLoad(options) {
    // 获取结果 URL、原图 URL、消耗和模式
    const { resultUrl, originalUrl, cost, mode, extractedUrl } = options

    // 优先使用 resultUrl，如果不存在则使用 extractedUrl（用于发型提取）
    const finalResultUrl = resultUrl || extractedUrl || ''

    if (!finalResultUrl) {
      wx.showToast({
        title: '参数错误',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
      return
    }

    // 解码 URL
    const decodedResultUrl = decodeURIComponent(finalResultUrl)
    const decodedOriginalUrl = originalUrl ? decodeURIComponent(originalUrl) : ''

    // 将相对路径转换为完整 URL（用于图片显示）
    const API_BASE_URL = 'http://192.168.1.3:5003'
    const displayResultUrl = decodedResultUrl.startsWith('/static/')
      ? API_BASE_URL + decodedResultUrl
      : decodedResultUrl
    const displayOriginalUrl = decodedOriginalUrl.startsWith('/static/')
      ? API_BASE_URL + decodedOriginalUrl
      : decodedOriginalUrl

    // 保存原始 URL 用于保存功能
    this.setData({
      rawResultUrl: decodedResultUrl,
      rawOriginalUrl: decodedOriginalUrl,
      cost: parseInt(cost) || 0,
      mode: mode || 'normal',
      showComparison: !!(mode && originalUrl)
    })

    // 真机显示：下载图片到本地临时文件
    this.downloadImageForDisplay(displayResultUrl, 'resultUrl')
    if (displayOriginalUrl) {
      this.downloadImageForDisplay(displayOriginalUrl, 'originalUrl')
    }

    // 计算消耗明细
    this.calculateCost()

    // 刷新用户信息获取最新余额
    this.loadUserInfo()
  },

  /**
   * 下载图片到本地用于真机显示
   */
  downloadImageForDisplay(url, dataKey) {
    wx.downloadFile({
      url: url,
      success: (res) => {
        if (res.statusCode === 200) {
          console.log('图片下载成功:', dataKey, res.tempFilePath)
          this.setData({
            [dataKey]: res.tempFilePath
          })
        } else {
          console.error('图片下载失败:', dataKey, res.statusCode)
          // 下载失败，使用原 URL
          this.setData({
            [dataKey]: url
          })
        }
      },
      fail: (err) => {
        console.error('图片下载失败:', dataKey, err)
        // 下载失败，使用原 URL
        this.setData({
          [dataKey]: url
        })
      }
    })
  },

  /**
   * 加载用户信息
   */
  async loadUserInfo() {
    try {
      const res = await refreshUserInfo()
      if (res.success) {
        const userInfo = res.user
        const isPremium = userInfo.member_level === 'premium'
        const totalHairs = (userInfo.scissor_hairs || 0) + (userInfo.comb_hairs || 0)

        this.setData({
          remainingHairs: totalHairs
        })
      }
    } catch (e) {
      console.error('加载用户信息失败:', e)
    }
  },

  /**
   * 计算消耗明细
   */
  calculateCost() {
    const cost = this.data.cost

    // 判断会员身份
    const userInfo = getUserInfo() || {}
    const isPremium = userInfo.member_level === 'premium'

    // 会员 50% 优惠
    const actualCost = isPremium ? Math.ceil(cost / 2) : cost

    // 优先从梳子槽扣费
    let combCost = 0
    let scissorCost = 0

    if (userInfo.comb_hairs >= actualCost) {
      combCost = actualCost
    } else {
      combCost = userInfo.comb_hairs || 0
      scissorCost = actualCost - combCost
    }

    this.setData({
      combCost,
      scissorCost
    })
  },

  /**
   * 放大图片
   */
  enlargeImage(e) {
    const src = e.currentTarget.dataset.src
    wx.previewImage({
      urls: [src],
      current: src
    })
  },

  /**
   * 保存图片到相册（通用方法）
   */
  async saveImageToAlbum(imageUrl, successMsg = '保存成功') {
    try {
      // 获取完整的图片 URL
      let fullUrl = imageUrl

      // 如果是相对路径，转换为完整 URL
      if (imageUrl && imageUrl.startsWith('/static/')) {
        fullUrl = 'http://192.168.1.3:5003' + imageUrl
      }

      // 如果已经是 http 开头，直接使用
      if (fullUrl && !fullUrl.startsWith('http://') && !fullUrl.startsWith('https://')) {
        fullUrl = 'http://localhost:5003' + fullUrl
      }

      wx.showLoading({ title: '保存中...' })

      // 方法 1: 使用 getImageInfo 获取图片本地路径
      wx.getImageInfo({
        src: fullUrl,
        success: (imageRes) => {
          console.log('图片加载成功，路径:', imageRes.path)

          // 保存到其他相册（使用 saveImageToPhotosAlbum）
          wx.saveImageToPhotosAlbum({
            filePath: imageRes.path,
            success: () => {
              wx.hideLoading()
              wx.showToast({
                title: successMsg,
                icon: 'success'
              })
            },
            fail: (err) => {
              wx.hideLoading()
              console.error('保存到相册失败:', err)

              // 检查是否是权限问题
              if (err.errMsg && err.errMsg.includes('auth deny')) {
                wx.showModal({
                  title: '提示',
                  content: '需要授权保存权限，是否前往设置？',
                  success: (modalRes) => {
                    if (modalRes.confirm) {
                      wx.openSetting()
                    }
                  }
                })
              } else {
                // 开发者工具可能不支持 saveImageToPhotosAlbum
                // 使用长按保存作为备选方案
                wx.showModal({
                  title: '提示',
                  content: '开发者工具限制，请在手机上测试或长按图片保存',
                  showCancel: false
                })
              }
            }
          })
        },
        fail: (err) => {
          wx.hideLoading()
          console.error('获取图片信息失败:', err)
          wx.showModal({
            title: '提示',
            content: '图片加载失败，请尝试长按图片选择保存到手机',
            showCancel: false
          })
        }
      })
    } catch (e) {
      wx.hideLoading()
      console.error('保存失败:', e)
      wx.showToast({
        title: '保存失败',
        icon: 'none'
      })
    }
  },

  /**
   * 保存原图到相册
   */
  async saveOriginalToAlbum() {
    this.saveImageToAlbum(this.data.rawOriginalUrl || this.data.originalUrl, '保存成功')
  },

  /**
   * 保存结果到相册
   */
  async saveToAlbum() {
    this.saveImageToAlbum(this.data.rawResultUrl || this.data.resultUrl, '保存成功')
  },

  /**
   * 返回首页
   */
  goHome() {
    wx.switchTab({
      url: '/pages/index/index'
    })
  }
})
