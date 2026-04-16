// pages/index/index.js
import { uploadFile } from '../../utils/request.js'
import { requireLogin, optionalLogin, isPremium, checkPremium, refreshUserInfo } from '../../utils/auth.js'
import { setRedirectUrl } from '../../utils/storage.js'
import { PRICING, SERVICE_TYPES, MODEL_VERSIONS, MODEL_VERSION_NAMES, SKETCH_STYLES } from '../../utils/constants.js'
import { transferHair, extractHair, addSketch } from '../../api/hair.js'
import { checkBalance } from '../../api/user.js'

Page({
  data: {
    // 余额
    scissorHairs: 0,
    combHairs: 0,
    totalHairs: 0,
    isPremium: false,
    isLoggedIn: false,    // 是否已登录

    // 图片
    hairstyleUrl: '',      // 显示用（临时文件路径）
    customerUrl: '',       // 显示用（临时文件路径）
    hairstyleHttpUrl: '',  // API 用（HTTP URL）
    customerHttpUrl: '',   // API 用（HTTP URL）

    // 参数
    modelVersions: ['脸型适配', '保持脸型'],
    modelVersionIndex: 0,
    fusionDegree: 70,
    enableSketch: false,
    sketchStyles: SKETCH_STYLES,
    sketchStyleIndex: 0,

    // 消耗
    currentCost: 0,
    allCost: 88,

    // 状态
    processing: false,
    processingText: '处理中...',

    // 分步模式状态
    modeIndex: 0,           // 0 = 综合模式, 1 = 分步模式 - 默认为综合模式
    modeInitialized: false, // 是否已经初始化过模式，避免每次onShow都重置
    hasResult: false,        // 是否已有发型迁移结果
    resultUrl: '',           // 发型迁移结果URL
    resultTaskId: ''         // 发型迁移任务ID
  },

  onShow() {
    // 刷新用户信息和余额
    this.loadUserInfo()

    // 只有在第一次进入页面时才设置默认模式，避免每次onShow都重置用户选择
    if (!this.data.modeInitialized) {
      this.setData({
        modeIndex: 0,      // 确保默认综合模式
        enableSketch: false, // 确保开关默认关闭
        modeInitialized: true // 标记已初始化
      })
    }
  },

  /**
   * 加载用户信息
   */
  async loadUserInfo() {
    try {
      const res = await refreshUserInfo()
      if (res.success) {
        const userInfo = res.user
        const isPremium = userInfo.member_level === 'vip'
        const totalHairs = (userInfo.scissor_hairs || 0) + (userInfo.comb_hairs || 0)

        // 计算价格（会员优惠）
        const pricing = isPremium ? PRICING.premium : PRICING.normal

        this.setData({
          scissorHairs: userInfo.scissor_hairs || 0,
          combHairs: userInfo.comb_hairs || 0,
          totalHairs: totalHairs,
          isPremium: isPremium,
          allCost: pricing.combined,
          isLoggedIn: true
        })
      }
    } catch (e) {
      console.error('加载用户信息失败:', e)
      // 访客模式：设置默认值
      this.setData({
        scissorHairs: 0,
        combHairs: 0,
        totalHairs: 0,
        isPremium: false,
        isLoggedIn: false,
        allCost: PRICING.normal.combined
      })
    }
  },

  /**
   * 选择发型参考图
   */
  async chooseHairstyleImage() {
    const res = await this.chooseImage()
    if (res) {
      this.uploadImage(res, 'hairstyle')
    }
  },

  /**
   * 选择客户照片
   */
  async chooseCustomerImage() {
    const res = await this.chooseImage()
    if (res) {
      this.uploadImage(res, 'customer')
    }
  },

  /**
   * 选择图片
   */
  chooseImage() {
    return new Promise((resolve) => {
      wx.chooseMedia({
        count: 1,
        mediaType: ['image'],
        sourceType: ['album', 'camera'],
        sizeType: ['compressed'],
        success: (res) => {
          resolve(res.tempFiles[0].tempFilePath)
        },
        fail: () => {
          resolve(null)
        }
      })
    })
  },

  /**
   * 上传图片
   */
  async uploadImage(filePath, type) {
    wx.showLoading({ title: '上传中...' })

    try {
      const res = await uploadFile(filePath)

      if (res.success && res.url) {
        const displayKey = type === 'hairstyle' ? 'hairstyleUrl' : 'customerUrl'
        const httpKey = type === 'hairstyle' ? 'hairstyleHttpUrl' : 'customerHttpUrl'

        // 将相对路径转换为完整 URL（API 调用需要）
        const API_BASE_URL = 'http://192.168.1.3:5003'
        const fullHttpUrl = res.url.startsWith('/static/')
          ? API_BASE_URL + res.url
          : res.url

        console.log('图片上传成功:', { type, url: res.url, fullHttpUrl })

        // 保存 HTTP URL 用于 API 调用
        this.setData({
          [httpKey]: fullHttpUrl
        })

        // 真机显示：下载图片到本地临时文件
        wx.downloadFile({
          url: fullHttpUrl,
          success: (downloadRes) => {
            if (downloadRes.statusCode === 200) {
              console.log('图片下载成功:', downloadRes.tempFilePath)
              this.setData({
                [displayKey]: downloadRes.tempFilePath
              })
            } else {
              console.error('图片下载失败:', downloadRes.statusCode)
              // 下载失败，使用原 URL
              this.setData({
                [displayKey]: fullHttpUrl
              })
            }
            wx.hideLoading()
          },
          fail: (err) => {
            console.error('图片下载失败:', err)
            // 下载失败，使用原 URL
            this.setData({
              [displayKey]: fullHttpUrl
            })
            wx.hideLoading()
          }
        })
      } else {
        throw new Error(res.error || '上传失败')
      }
    } catch (e) {
      console.error('上传图片失败:', e)
      wx.hideLoading()
      wx.showToast({
        title: e.error || '上传失败',
        icon: 'none'
      })
    }
  },

  /**
   * 删除发型参考图
   */
  deleteHairstyleImage() {
    this.setData({
      hairstyleUrl: '',
      hairstyleHttpUrl: ''
    })
  },

  /**
   * 删除客户照片
   */
  deleteCustomerImage() {
    this.setData({
      customerUrl: '',
      customerHttpUrl: ''
    })
  },

  /**
   * 模型版本改变
   */
  onModelVersionChange(e) {
    this.setData({
      modelVersionIndex: parseInt(e.detail.value)
    })
  },

  /**
   * 融合度改变
   */
  onFusionDegreeChange(e) {
    this.setData({
      fusionDegree: e.detail.value
    })
  },

  /**
   * 素描效果开关
   */
  onSketchChange(e) {
    this.setData({
      enableSketch: e.detail.value
    })
  },

  /**
   * 素描风格改变
   */
  onSketchStyleChange(e) {
    this.setData({
      sketchStyleIndex: parseInt(e.detail.value)
    })
  },

  /**
   * 处理模式改变
   */
  onModeChange(e) {
    const newModeIndex = parseInt(e.detail.value)
    console.log('模式切换:', this.data.modeIndex, '->', newModeIndex)

    // 如果从分步模式切换到综合模式，重置中间结果
    const updateData = { modeIndex: newModeIndex }
    if (this.data.modeIndex === 1 && newModeIndex === 0) {
      updateData.hasResult = false
      updateData.resultUrl = ''
      updateData.resultTaskId = ''
      console.log('重置分步模式中间结果')
    }

    this.setData(updateData)

    wx.showToast({
      title: newModeIndex === 1 ? '已切换到分步模式' : '已切换到综合模式',
      icon: 'none'
    })
  },

  /**
   * 放大图片预览
   */
  enlargeImage(e) {
    const src = e.currentTarget.dataset.src
    wx.previewImage({
      urls: [src],
      current: src
    })
  },

  /**
   * 仅提取发型
   */
  async extractOnly() {
    if (!this.data.hairstyleUrl) {
      wx.showToast({
        title: '请先上传发型参考图',
        icon: 'none'
      })
      return
    }

    const cost = this.data.isPremium ? 2 : 4
    if (!await this.checkBalanceAndLogin(cost)) {
      return
    }

    await this.callExtractAPI()
  },

  /**
   * 仅迁移发型
   */
  async transferOnly() {
    if (!this.data.hairstyleUrl || !this.data.customerUrl) {
      wx.showToast({
        title: '请先上传两张图片',
        icon: 'none'
      })
      return
    }

    const cost = this.data.isPremium ? 2 : 4
    if (!await this.checkBalanceAndLogin(cost)) {
      return
    }

    // 分步模式：保存结果用于后续生成素描；综合模式：直接跳转到结果页
    const saveResult = this.data.modeIndex === 1  // 分步模式（modeIndex=1）时保存
    await this.callTransferAPI(false, saveResult)
  },

  /**
   * 素描优化（分步模式第二步，新增）
   */
  async addSketchOnly() {
    // 访客也可以体验，不强制登录
      return
    }

    if (!this.data.hasResult) {
      wx.showToast({
        title: '请先生成发型',
        icon: 'none'
      })
      return
    }

    const cost = this.data.isPremium ? 44 : 88  // 分步模式第2步：sketch_step 定价
    if (!await this.checkBalanceAndLogin(cost)) {
      return
    }

    wx.showLoading({ title: '生成素描中...' })

    try {
      const params = {
        result_url: this.data.resultUrl,
        sketch_style: this.data.sketchStyles[this.data.sketchStyleIndex].value,
        step_by_step: true  // 分步模式第2步
      }

      const res = await addSketch(params)

      wx.hideLoading()

      if (res.success) {
        wx.showToast({
          title: `素描优化成功，已扣费${res.cost}发丝`,
          icon: 'success',
          duration: 2000
        })

        // 将相对路径转换为完整 URL（真机显示需要）
        const API_BASE_URL = 'http://192.168.1.3:5003'
        const fullSketchUrl = res.sketch_url.startsWith('/static/')
          ? API_BASE_URL + res.sketch_url
          : res.sketch_url

        // 跳转到结果页，显示原图和素描
        wx.navigateTo({
          url: `/pages/result/result?resultUrl=${encodeURIComponent(fullSketchUrl)}&originalUrl=${encodeURIComponent(this.data.resultUrl)}&cost=${res.cost}&mode=sketch`
        })
      } else {
        throw new Error(res.error || '处理失败')
      }
    } catch (e) {
      wx.hideLoading()
      console.error('素描优化失败:', e)
      wx.showToast({
        title: e.error || '处理失败',
        icon: 'none'
      })
    } finally {
      // 确保无论成功或失败都重置处理状态
      this.setData({
        processing: false
      })
    }
  },

  /**
   * 切换处理模式
   */
  switchMode() {
    const newModeIndex = this.data.modeIndex === 0 ? 1 : 0
    console.log('模式切换:', this.data.modeIndex, '->', newModeIndex)

    // 如果从分步模式切换到综合模式，重置中间结果
    const updateData = { modeIndex: newModeIndex }
    if (this.data.modeIndex === 1 && newModeIndex === 0) {
      updateData.hasResult = false
      updateData.resultUrl = ''
      updateData.resultTaskId = ''
      console.log('重置分步模式中间结果')
    }

    this.setData(updateData)

    wx.showToast({
      title: newModeIndex === 1 ? '已切换到分步模式' : '已切换到综合模式',
      icon: 'none'
    })
  },

  /**
   * 素描优化（综合模式）
   */
  async processAll() {
    if (!this.data.hairstyleUrl || !this.data.customerUrl) {
      wx.showToast({
        title: '请先上传两张图片',
        icon: 'none'
      })
      return
    }

    // 检查素描效果开关
    if (!this.data.enableSketch) {
      wx.showToast({
        title: '请先打开素描效果按钮',
        icon: 'none'
      })
      return
    }

    const cost = this.data.allCost
    if (!await this.checkBalanceAndLogin(cost)) {
      return
    }

    await this.callTransferAPI(this.data.enableSketch)
  },

  /**
   * 检查余额
   */
  async checkBalance(cost) {
    if (this.data.totalHairs < cost) {
      return new Promise((resolve) => {
        wx.showModal({
          title: '余额不足',
          content: `发丝不足，现在充值立即可用，或 4 小时后使用免费额度`,
          confirmText: '去充值',
          cancelText: '取消',
          success: (res) => {
            if (res.confirm) {
              wx.navigateTo({
                url: '/pages/balance/balance'
              })
            }
            resolve(false)
          },
          fail: () => resolve(false)
        })
      })
    }
    return true
  },

  /**
   * 检查余额并提示登录
   * 如果余额不足或用户未登录，显示相应提示
   */
  async checkBalanceAndLogin(cost) {
    // 如果未登录，提示登录
    if (!this.data.isLoggedIn) {
      return new Promise((resolve) => {
        wx.showModal({
          title: '提示',
          content: `登录后即可使用全部功能，消耗发丝扣费，是否立即登录？`,
          confirmText: '去登录',
          cancelText: '暂不',
          success: (res) => {
            if (res.confirm) {
              // 保存当前路径
              setRedirectUrl('/pages/index/index')
              wx.navigateTo({
                url: '/pages/login/login'
              })
              resolve(false)
            } else {
              // 用户选择暂不登录，不允许继续操作
              resolve(false)
            }
          },
          fail: () => resolve(false)
        })
      })
    }

    // 已登录用户，检查余额
    if (this.data.totalHairs < cost) {
      return new Promise((resolve) => {
        wx.showModal({
          title: '余额不足',
          content: `发丝不足，现在充值立即可用，或 4 小时后使用免费额度`,
          confirmText: '去充值',
          cancelText: '取消',
          success: (res) => {
            if (res.confirm) {
              wx.navigateTo({
                url: '/pages/balance/balance'
              })
            }
            resolve(false)
          },
          fail: () => resolve(false)
        })
      })
    }
    return true
  },

  /**
   * 调用提取发型API
   */
  async callExtractAPI() {
    this.setData({
      processing: true,
      processingText: '提取发型中...'
    })

    try {
      const res = await extractHair({
        image_url: this.data.hairstyleHttpUrl
      })

      if (res.success) {
        // 将相对路径转换为完整 URL（真机显示需要）
        const API_BASE_URL = 'http://192.168.1.3:5003'
        const fullResultUrl = res.result_url.startsWith('/static/')
          ? API_BASE_URL + res.result_url
          : res.result_url

        this.navigateToResult(fullResultUrl, res.cost)
      } else {
        throw new Error(res.error || '处理失败')
      }
    } catch (e) {
      console.error('提取发型失败:', e)
      wx.showToast({
        title: e.error || '处理失败',
        icon: 'none'
      })
    } finally {
      this.setData({
        processing: false
      })
    }
  },

  /**
   * 调用发型迁移API
   * @param {boolean} enableSketch - 是否启用素描
   * @param {boolean} saveResult - 是否保存结果用于分步模式
   */
  async callTransferAPI(enableSketch, saveResult = false) {
    const modelVersion = this.data.modelVersionIndex === 0 ? 'v1' : 'v2'
    const fusionDegree = this.data.fusionDegree / 100

    this.setData({
      processing: true,
      processingText: enableSketch ? '综合处理中...' : '迁移发型中...'
    })

    try {
      const params = {
        hairstyle_image: this.data.hairstyleHttpUrl,
        customer_image: this.data.customerHttpUrl,
        model_version: modelVersion,
        fusion_degree: fusionDegree,
        step_by_step: this.data.modeIndex === 1  // 分步模式（modeIndex=1）时传递true
      }

      // 如果启用素描，添加参数
      if (enableSketch) {
        params.enable_sketch = true
        params.sketch_style = this.data.sketchStyles[this.data.sketchStyleIndex].value
      }

      const res = await transferHair(params)

      if (res.success) {
        // 保存结果用于分步模式
        if (saveResult) {
          // 将相对路径转换为完整 URL（真机显示需要）
          const API_BASE_URL = 'http://192.168.1.3:5003'
          const fullResultUrl = res.result_url.startsWith('/static/')
            ? API_BASE_URL + res.result_url
            : res.result_url

          // 真机显示：下载图片到本地临时文件
          const self = this
          wx.downloadFile({
            url: fullResultUrl,
            success: (downloadRes) => {
              if (downloadRes.statusCode === 200) {
                console.log('分步模式结果图片下载成功:', downloadRes.tempFilePath)
                self.setData({
                  hasResult: true,
                  resultUrl: downloadRes.tempFilePath,  // 使用临时文件路径显示
                  resultTaskId: res.task_id,
                  enableSketch: true  // 自动开启素描效果开关
                })
              } else {
                console.error('分步模式结果图片下载失败:', downloadRes.statusCode)
                self.setData({
                  hasResult: true,
                  resultUrl: fullResultUrl,  // 下载失败，使用原 URL
                  resultTaskId: res.task_id,
                  enableSketch: true
                })
              }
            },
            fail: (err) => {
              console.error('分步模式结果图片下载失败:', err)
              self.setData({
                hasResult: true,
                resultUrl: fullResultUrl,  // 下载失败，使用原 URL
                resultTaskId: res.task_id,
                enableSketch: true
              })
            }
          })

          // 分步模式：显示原图和扣费信息，不跳转到结果页
          wx.showToast({
            title: `发型生成成功，已扣费${res.cost}发丝`,
            icon: 'success',
            duration: 2000
          })
        } else {
          // 综合模式：直接跳转到结果页
          // 将相对路径转换为完整 URL（真机显示需要）
          const API_BASE_URL = 'http://192.168.1.3:5003'

          // 如果启用了素描且有 sketch_url，跳转到素描结果；否则跳转到原图
          let finalUrl = (enableSketch && res.sketch_url) ? res.sketch_url : res.result_url
          finalUrl = finalUrl.startsWith('/static/') ? API_BASE_URL + finalUrl : finalUrl

          console.log('综合模式跳转:', { enableSketch, hasSketchUrl: !!res.sketch_url, finalUrl })

          if (enableSketch && res.sketch_url) {
            // 有素描结果：显示原图和素描对比
            const fullSketchUrl = res.sketch_url.startsWith('/static/')
              ? API_BASE_URL + res.sketch_url
              : res.sketch_url
            const fullResultUrl = res.result_url.startsWith('/static/')
              ? API_BASE_URL + res.result_url
              : res.result_url

            wx.navigateTo({
              url: `/pages/result/result?resultUrl=${encodeURIComponent(fullSketchUrl)}&originalUrl=${encodeURIComponent(fullResultUrl)}&cost=${res.cost}&mode=sketch`
            })
          } else {
            // 没有素描：只显示原图
            this.navigateToResult(finalUrl, res.cost)
          }
        }
      } else {
        throw new Error(res.error || '处理失败')
      }
    } catch (e) {
      console.error('发型迁移失败:', e)
      wx.showToast({
        title: e.error || '处理失败',
        icon: 'none'
      })
    } finally {
      this.setData({
        processing: false
      })
    }
  },

  /**
   * 跳转到结果页
   */
  navigateToResult(resultUrl, cost) {
    wx.navigateTo({
      url: `/pages/result/result?resultUrl=${encodeURIComponent(resultUrl)}&cost=${cost}`
    })
  },

  /**
   * 跳转到会员中心
   */
  goToMember() {
    wx.navigateTo({
      url: '/pages/member/member'
    })
  },

  /**
   * 跳转到登录页
   */
  goToLogin() {
    wx.navigateTo({
      url: '/pages/login/login'
    })
  },

  /**
   * 图片加载成功
   */
  imageLoad(e) {
    console.log('图片加载成功:', e.currentTarget.dataset.src || e.target.src)
  },

  /**
   * 图片加载失败
   */
  imageError(e) {
    console.error('图片加载失败:', e.detail.errMsg, 'URL:', e.currentTarget.dataset.src || e.target.src)
    wx.showToast({
      title: '图片加载失败',
      icon: 'none'
    })
  }
})
