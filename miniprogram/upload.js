/**
 * 微信小程序代码上传脚本
 * 使用 miniprogram-ci 自动上传
 */

const ci = require('miniprogram-ci')
const path = require('path')

;(async () => {
  console.log('🚀 开始上传微信小程序...')
  console.log('')
  console.log('📋 上传配置:')
  console.log('   AppID: wxfd9b1af6c0b5908e')
  console.log('   项目路径:', path.join(__dirname))
  console.log('   私钥文件:', path.join(__dirname, 'private.key'))
  console.log('')

  try {
    // 创建项目对象
    const project = new ci.Project({
      appid: 'wxfd9b1af6c0b5908e',
      type: 'miniProgram',
      projectPath: __dirname,
      privateKeyPath: path.join(__dirname, 'private.key'),
      ignores: ['node_modules/**/*', '.claude/**/*', '.worktrees/**/*', '*.tmp'],
    })

    console.log('✅ 项目对象创建成功，开始上传...')
    console.log('')

    // 执行上传
    const uploadResult = await ci.upload({
      project,
      version: '1.0.0',
      desc: '发型迁移小程序 - 首次发布',
      setting: {
        es6: true,
        es7: true,
        minify: true,
        minifyWXML: true,
        minifyWXSS: true,
        ignoreDevUnusedFiles: true,
      },
      onProgressUpdate: (info) => {
        console.log(`📊 上传进度：${info.progress}%`)
      },
    })

    console.log('')
    console.log('✅ 上传成功!')
    console.log('')
    console.log('📦 包信息:', uploadResult.subPackageInfo)
    console.log('')
    console.log('📱 预览:')
    console.log('   - 登录微信公众平台查看预览二维码')
    console.log('   - 或查看下方显示的二维码')

  } catch (error) {
    console.error('')
    console.error('❌ 上传失败:', error.message)
    console.error('')
    console.error('常见错误及解决方法:')
    console.error('   1. IP 白名单未配置')
    console.error('      → 微信公众平台 → 开发设置 → IP 白名单 → 添加你的公网 IP 144.7.70.159')
    console.error('')
    console.error('   2. 私钥文件无效')
    console.error('      → 确认已从微信公众平台正确下载密钥')
    console.error('')
    console.error('   3. 版本号低于当前版本')
    console.error('      → 修改 version 版本号')
    console.error('')
    console.error('错误详情:', error)
    process.exit(1)
  }
})()
