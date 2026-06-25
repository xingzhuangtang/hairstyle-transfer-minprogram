// pages/about/about.js
import { onLocaleChange } from '../../utils/i18n.js'
const app = getApp()

Page({
  data: {
    version: 'V1.1',
    delta: '0.001',
    tAppName: '',
    tDeltaLabel: '',
    tAppDesc: '',
    tPoweredByQoder: '',
    tPoweredByClaude: ''
  },

  onLoad() {
    this._loadI18n()
    this._setupLocaleListener()
    app.setNavTitle(this, 'about.title')
  },

  onShow() {
    this._loadI18n()
    app.setNavTitle(this, 'about.title')
  },

  _setupLocaleListener() {
    onLocaleChange(() => {
      this._loadI18n()
      app.setNavTitle(this, 'about.title')
    })
  },

  _loadI18n() {
    const t = (key) => app.t(key)
    this.setData({
      tAppName: t('app.name'),
      tDeltaLabel: t('about.delta'),
      tAppDesc: t('about.intro'),
      tPoweredByQoder: 'Powered by Qoder Code CLI',
      tPoweredByClaude: 'Powered by Claude Code CLI'
    })
  }
})
