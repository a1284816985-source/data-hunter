<template>
  <div class="page-container">
    <h1 class="text-2xl font-bold mb-6">系统设置</h1>

    <!-- 平台账号管理 -->
    <div class="card mb-6">
      <h2 class="text-lg font-medium mb-4">平台账号管理</h2>
      <p class="text-sm text-gray-400 mb-4">管理各平台的登录状态（Cookie），用于爬虫采集时保持登录</p>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div v-for="p in platforms" :key="p.value" class="border rounded-lg p-4">
          <div class="flex items-center justify-between mb-3">
            <span class="font-medium">{{ p.label }}</span>
            <span :class="getAccountStatus(p.value) === 'active' ? 'badge badge-success' : 'badge badge-error'">
              {{ getAccountStatus(p.value) === 'active' ? '✅ 已登录' : '⚠️ 未登录' }}
            </span>
          </div>
          <div v-if="getAccount(p.value)" class="text-xs text-gray-400 mb-2">
            最后验证：{{ getAccount(p.value).last_verified || '无' }}
          </div>

          <!-- Cookie 输入 -->
          <div class="mb-3">
            <label class="text-xs text-gray-500">Cookie JSON（从浏览器开发者工具复制）</label>
            <textarea
              v-model="cookieInputs[p.value]"
              class="input-field !text-xs !py-1.5 mt-1"
              rows="3"
              placeholder='[{"name":"...","value":"..."}]'
            ></textarea>
          </div>

          <div class="flex gap-2">
            <button @click="saveAccount(p.value)" class="btn-primary text-sm !px-3 !py-1.5">💾 保存</button>
            <button v-if="getAccount(p.value)" @click="deleteAccount(p.value)" class="btn-danger text-sm !px-3 !py-1.5">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 使用说明 -->
    <div class="card">
      <h2 class="text-lg font-medium mb-4">📖 使用说明</h2>
      <div class="space-y-3 text-sm text-gray-600">
        <div>
          <p class="font-medium text-gray-800 mb-1">1. 配置平台账号</p>
          <p>先在浏览器中登录对应平台，然后从开发者工具(F12) → Application → Cookies 中复制 Cookie 数据，粘贴到上方对应平台。</p>
        </div>
        <div>
          <p class="font-medium text-gray-800 mb-1">2. 创建采集任务</p>
          <p>到「采集任务」页面，输入关键词、选择平台和类型，点击开始采集。任务在后台异步执行。</p>
        </div>
        <div>
          <p class="font-medium text-gray-800 mb-1">3. 查看数据</p>
          <p>任务完成后，到「数据浏览」查看采集结果。支持按平台筛选、价格排序、导出 Excel。</p>
        </div>
        <div>
          <p class="font-medium text-gray-800 mb-1">4. 生成报告</p>
          <p>在数据浏览或 AI 报告页面，一键生成分析报告，包含价格对比、销量趋势、情感分析、策略建议等维度。</p>
        </div>
        <div>
          <p class="font-medium text-gray-800 mb-1">5. 爆款仿写</p>
          <p>在图文/视频数据浏览中，点击任意内容的「爆款仿写」，输入你的产品主题，AI 自动生成类似风格的文案。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { accountApi } from '../api'

const platforms = [
  { value: 'taobao', label: '🍑 淘宝' },
  { value: 'xiaohongshu', label: '📕 小红书' },
  { value: 'douyin', label: '🎵 抖音' },
  { value: 'meituan', label: '🍔 美团' },
  { value: 'amazon', label: '📦 亚马逊' },
]

const accounts = ref<any[]>([])
const cookieInputs = ref<Record<string, string>>({})

function getAccount(platform: string) {
  return accounts.value.find((a: any) => a.platform === platform)
}

function getAccountStatus(platform: string) {
  return getAccount(platform)?.status || 'inactive'
}

async function loadAccounts() {
  try {
    const res = await accountApi.list()
    accounts.value = res.data
  } catch {}
}

async function saveAccount(platform: string) {
  const raw = cookieInputs.value[platform] || ''
  let cookies = {}
  try {
    cookies = JSON.parse(raw)
  } catch {
    alert('Cookie 格式错误，请输入有效的 JSON 数组')
    return
  }
  try {
    await accountApi.upsert(platform, { cookies })
    cookieInputs.value[platform] = ''
    await loadAccounts()
  } catch {}
}

async function deleteAccount(platform: string) {
  const account = getAccount(platform)
  if (account && confirm(`确定删除 ${platformLabel(platform)} 的账号信息？`)) {
    await accountApi.delete(account.id)
    await loadAccounts()
  }
}

function platformLabel(p: string) {
  const m: Record<string, string> = { taobao: '淘宝', xiaohongshu: '小红书', douyin: '抖音', meituan: '美团', amazon: '亚马逊' }
  return m[p] || p
}

onMounted(loadAccounts)
</script>
