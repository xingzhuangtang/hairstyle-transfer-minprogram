export const API_BASE_URL = "http://192.168.1.3:5003"

// 存储键位定义
export const STORAGE_KEYS = {
  TOKEN: 'token',
  USER_INFO: 'user_info',
  PENDING_ORDERS: 'pending_orders',
  REDIRECT_URL: 'redirect_url'
}

// 价格配置
export const PRICING = {
  normal: {
    hairSegment: 4,
    faceMerge: 4,
    sketch: 84,
    combined: 88
  },
  vip: {
    hairSegment: 2,
    faceMerge: 2,
    sketch: 42,
    combined: 46
  }
}

// 服务类型
export const SERVICE_TYPES = {
  HAIR_SEGMENT: 'hair_segment',
  FACE_MERGE: 'face_merge',
  SKETCH: 'sketch',
  COMBINED: 'combined'
}

// 模型版本
export const MODEL_VERSIONS = ['v1', 'v2']
export const MODEL_VERSION_NAMES = ['脸型适配', '保持脸型']

// 素描风格
export const SKETCH_STYLES = [
  { label: '铅笔素描', value: 'pencil' },
  { label: '日式动漫', value: 'anime' },
  { label: '水墨风格', value: 'ink' },
  { label: '淡彩素描', value: 'vivid' }
]

// 充值规则配置
export const RECHARGE_RULES = [
  { amount: 10, scissorHairs: 1000, combHairs: 0, bonus: 0 },
  { amount: 20, scissorHairs: 2000, combHairs: 88, bonus: 88, recommended: true },
  { amount: 50, scissorHairs: 5000, combHairs: 588, bonus: 588 },
  { amount: 100, scissorHairs: 10000, combHairs: 1688, bonus: 1688 }
]

// 会员配置
export const MEMBER_CONFIG = {
  price: 99,
  durationDays: 365,
  bonusHairs: 1000
}

// 余额不足自动赠送配置
export const INSUFFICIENT_BONUS_CONFIG = {
  checkAfterHours: 4,        // 4 小时后检查
  cooldownHours: 4,          // 4 小时间隔
  maxBonusTimesPerYear: 36,  // 36 次/年上限
  normalUserBonus: 188,      // 普通用户赠送量
  vipUserBonus: 98       // VIP 用户赠送量
}
