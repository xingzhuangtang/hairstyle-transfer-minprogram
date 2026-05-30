/**
 * 设备 ID 工具
 * 基于设备信息生成确定性哈希，同一设备永远生成相同 ID
 */

/**
 * 获取或生成设备 ID（持久化到 storage，永不改变）
 */
export function getDeviceId() {
  let deviceId = wx.getStorageSync('device_id')
  if (deviceId) {
    return deviceId
  }

  deviceId = generateDeviceId()
  wx.setStorageSync('device_id', deviceId)
  return deviceId
}

/**
 * 生成设备 ID（不读写 storage，纯计算）
 */
export function generateDeviceId() {
  const systemInfo = wx.getSystemInfoSync()
  const uniqueStr = `${systemInfo.brand}-${systemInfo.model}-${systemInfo.system}-${systemInfo.platform}`
  let hash = 0
  for (let i = 0; i < uniqueStr.length; i++) {
    const char = uniqueStr.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash
  }
  return `device_${Math.abs(hash).toString(16).padStart(8, '0')}`
}

/**
 * 获取设备信息（包含 device_id 和显示名称）
 */
export function getDeviceInfo() {
  const systemInfo = wx.getSystemInfoSync()
  const deviceId = getDeviceId()
  return {
    device_id: deviceId,
    device_name: `${systemInfo.brand || '未知'} ${systemInfo.model || '未知'}`,
    device_type: 'mobile'
  }
}

export default {
  getDeviceId,
  generateDeviceId,
  getDeviceInfo
}
