<template>
  <div class="page-container">
    <h1 class="text-2xl font-bold mb-6">系统设置</h1>

    <!-- 平台账号管理 -->
    <div class="card mb-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-lg font-medium">平台账号管理</h2>
          <p class="text-sm text-gray-400">点击「扫码登录」打开浏览器窗口完成登录，系统自动捕获 Cookie</p>
        </div>
        <div class="flex gap-2">
          <button @click="verifyAll" class="btn-secondary text-sm !px-3 !py-1.5" :disabled="verifying">
            {{ verifying ? '检测中...' : '🔄 检测全部' }}
          </button>
          <span class="text-xs text-gray-400 self-center">每 5 分钟自动检测</span>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div v-for="p in platforms" :key="p.value" class="border rounded-lg p-4"
             :class="getAccountStatus(p.value) === 'active' ? 'border-green-200 bg-green-50/30' : 'border-gray-200'">
          
          <!-- 标题行 -->
          <div class="flex items-center justify-between mb-3">
            <span class="font-medium">{{ p.label }}</span>
            <span :class="statusBadge(getAccountStatus(p.value))">
              {{ statusText(getAccountStatus(p.value), loggingIn[p.value]) }}
            </span>
          </div>

          <!-- 信息行 -->
          <div v-if="getAccount(p.value)" class="text-xs text-gray-400 mb-3">
            <div v-if="getAccount(p.value).last_verified">
              🕐 最后检测：{{ getAccount(p.value).last_verified }}
            </div>
            <div v-if="getAccount(p.value).has_cookies">
              🍪 Cookie 数量：{{ getAccount(p.value).cookie_count || '已配置' }}
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex gap-2 flex-wrap">
            <button @click="startLogin(p.value)" 
                    class="btn-primary text-sm !px-3 !py-1.5"
                    :disabled="loggingIn[p.value]">
              {{ loggingIn[p.value] ? '⏳ 登录中...' : '📱 扫码登录' }}
            </button>
            <button @click="verifyOne(p.value)" 
                    class="btn-secondary text-sm !px-3 !py-1.5"
                    v-if="getAccount(p.value)?.has_cookies">
              🔍 检测
            </button>
            <button v-if="getAccount(p.value)" 
                    @click="deleteAccount(p.value)" 
                    class="btn-danger text-sm !px-3 !py-1.5">
              删除
            </button>
          </div>

          <!-- 登录提示 -->
          <div v-if="loginMsg[p.value]" 
               class="mt-3 text-xs rounded-lg p-2"
               :class="loginMsg[p.value].startsWith('✅') ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'">
            {{ loginMsg[p.value] }}
          </div>
        </div>
      </div>
    </div>

    <!-- 使用说明 -->
    <div class="card">
      <h2 class="text-lg font-medium mb-4">📖 使用说明</h2>
      <div class="space-y-3 text-sm text-gray-600">
        <div>
          <p class="font-medium text-gray-800 mb-1">1. 扫码登录平台</p>
          <p>点击对应平台的「📱 扫码登录」，浏览器窗口会打开登录页。用手机 App 扫码完成登录，系统自动捕获 Cookie。</p>
        </div>
        <div>
          <p class="font-medium text-gray-800 mb-1">2. 创建采集任务</p>
          <p>到「采集任务」页面，输入关键词、选择平台和类型，点击开始采集。任务在后台异步执行。</p>
        </div>
        <div>
          <p class="font-medium text-gray-800 mb-1">3. 查看数据</p>
          <p>任务完成后，到「数据浏览」查看采集结果。支持按平台筛选、排序、导出 Excel。</p>
        </div>
        <div>
          <p class="font-medium text-gray-800 mb-1">4. 生成报告</p>
          <p>在数据浏览或 AI 报告页面，一键生成四维分析报告。</p>
        </div>
        <div>
          <p class="font-medium text-gray-800 mb-1">5. 爆款仿写</p>
          <p>在图文/视频数据浏览中，点击任意内容的「爆款仿写」，AI 自动生成类似风格的文案。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { accountApi } from '../api'
import axios from 'axios'

const platforms = [
  { value: 'taobao', label: '🍑 淘宝' },
  { value: 'xiaohongshu', label: '📕 小红书' },
  { value: 'douyin', label: '🎵 抖音' },
  { value: 'meituan', label: '🍔 美团' },
  { value: 'amazon', label: '📦 亚马逊' },
]

const accounts = ref<any[]>([])
const loggingIn = reactive<Record<string, boolean>>({})
const loginMsg = reactive<Record<string, string>>({})
const verifying = ref(false)
let pollTimer: any = null

function getAccount(platform: string) {
  return accounts.value.find((a: any) => a.platform === platform)
}

function getAccountStatus(platform: string) {
  return getAccount(platform)?.status || 'inactive'
}

function statusBadge(status: string) {
  const m: Record<string, string> = {
    active: 'badge badge-success',
    expired: 'badge badge-error',
    inactive: 'badge',
    error: 'badge badge-warning',
  }
  return m[status] || 'badge'
}

function statusText(status: string, logging: boolean) {
  if (logging) return '⏳ 登录中'
  const m: Record<string, string> = {
    active: '✅ 已连接',
    expired: '⚠️ 已失效',
    inactive: '⬜ 未登录',
    error: '❌ 异常',
  }
  return m[status] || status
}

async function loadAccounts() {
  try {
    const res = await accountApi.list()
    accounts.value = res.data
  } catch {}
}

async function startLogin(platform: string) {
  loggingIn[platform] = true
  loginMsg[platform] = '🌐 浏览器窗口已打开，请扫码登录...'
  try {
    await axios.post(`/api/accounts/${platform}/login`)
    // 轮询登录状态
    let attempts = 0
    const check = setInterval(async () => {
      attempts++
      try {
        const res = await axios.get(`/api/accounts/${platform}/login-status`)
        const status = res.data.status
        if (status === 'done') {
          clearInterval(check)
          loggingIn[platform] = false
          loginMsg[platform] = '✅ 登录成功！Cookie 已保存'
          await loadAccounts()
          setTimeout(() => { loginMsg[platform] = '' }, 5000)
        } else if (status === 'failed' || status?.startsWith('error')) {
          clearInterval(check)
          loggingIn[platform] = false
          loginMsg[platform] = '❌ 登录失败：' + (status || '超时')
        } else if (attempts > 60) {
          clearInterval(check)
          loggingIn[platform] = false
          loginMsg[platform] = '⚠️ 超时，请重试'
        }
      } catch {
        clearInterval(check)
        loggingIn[platform] = false
      }
    }, 2000)
  } catch (e: any) {
    loggingIn[platform] = false
    loginMsg[platform] = '❌ ' + (e.response?.data?.detail || '启动失败')
  }
}

async function verifyOne(platform: string) {
  try {
    const res = await axios.post(`/api/accounts/${platform}/verify`)
    if (res.data.valid) {
      loginMsg[platform] = '✅ Cookie 有效'
    } else {
      loginMsg[platform] = '⚠️ Cookie 已失效，请重新登录'
    }
    await loadAccounts()
    setTimeout(() => { loginMsg[platform] = '' }, 3000)
  } catch {
    loginMsg[platform] = '❌ 检测失败'
  }
}

async function verifyAll() {
  verifying.value = true
  try {
    const res = await axios.post('/api/accounts/verify-all')
    await loadAccounts()
  } catch {}
  verifying.value = false
}

async function deleteAccount(platform: string) {
  const account = getAccount(platform)
  if (account && confirm(`确定删除 ${platformLabel(platform)} 的登录信息？`)) {
    await accountApi.delete(account.id)
    await loadAccounts()
  }
}

function platformLabel(p: string) {
  const m: Record<string, string> = { taobao: '淘宝', xiaohongshu: '小红书', douyin: '抖音', meituan: '美团', amazon: '亚马逊' }
  return m[p] || p
}

onMounted(() => {
  loadAccounts()
  // 每 5 分钟自动检测
  pollTimer = setInterval(verifyAll, 5 * 60 * 1000)
})

onUnmounted(() => {
  clearInterval(pollTimer)
})
</script>
