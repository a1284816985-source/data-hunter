<template>
  <div class="page-container">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">采集任务</h1>
      <button @click="showCreate = true" class="btn-primary">+ 新建采集任务</button>
    </div>

    <!-- 任务列表 -->
    <div class="card">
      <table class="w-full" v-if="tasks.length > 0">
        <thead>
          <tr class="text-left text-sm text-gray-500 border-b">
            <th class="pb-3 font-medium">关键词</th>
            <th class="pb-3 font-medium">平台</th>
            <th class="pb-3 font-medium">类型</th>
            <th class="pb-3 font-medium">数量</th>
            <th class="pb-3 font-medium">状态</th>
            <th class="pb-3 font-medium">时间</th>
            <th class="pb-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.id" class="border-b last:border-0 text-sm">
            <td class="py-3 font-medium">{{ task.keyword }}</td>
            <td class="py-3">
              <span v-for="p in task.platforms" :key="p" class="badge badge-info mr-1">{{ platformLabel(p) }}</span>
            </td>
            <td class="py-3">{{ task.task_type === 'product_group' ? '🛒 商品/团购' : '📱 图文/视频' }}</td>
            <td class="py-3">{{ task.total_items || '-' }}</td>
            <td class="py-3">
              <span :class="statusBadge(task.status)">{{ statusLabel(task.status) }}</span>
            </td>
            <td class="py-3 text-gray-400">{{ formatTime(task.created_at) }}</td>
            <td class="py-3">
              <div class="flex gap-2">
                <button v-if="task.status === 'completed'" @click="viewData(task.id)" class="text-primary-600 text-sm hover:underline">查看数据</button>
                <button v-if="task.status === 'completed'" @click="generateReport(task.id)" class="text-green-600 text-sm hover:underline">生成报告</button>
                <button v-if="task.status === 'queued'" @click="cancelTask(task.id)" class="text-yellow-600 text-sm hover:underline">取消</button>
                <button v-if="task.status !== 'running'" @click="deleteTask(task.id)" class="text-red-500 text-sm hover:underline">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="text-gray-400 text-center py-12">暂无任务，点击上方按钮创建第一个采集任务</p>
    </div>

    <!-- 新建任务弹窗 -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showCreate = false">
      <div class="bg-white rounded-xl shadow-xl p-8 w-[520px] max-h-[80vh] overflow-y-auto">
        <h2 class="text-xl font-bold mb-6">新建采集任务</h2>

        <!-- 关键词 -->
        <label class="block text-sm font-medium text-gray-600 mb-1">搜索关键词</label>
        <input v-model="form.keyword" class="input-field mb-4" placeholder="输入关键词，如：防晒霜" />

        <!-- 任务类型 -->
        <label class="block text-sm font-medium text-gray-600 mb-2">任务类型</label>
        <div class="flex gap-2 mb-4">
          <button
            v-for="t in taskTypes"
            :key="t.value"
            @click="form.task_type = t.value"
            class="flex-1 py-3 rounded-lg border-2 text-sm font-medium transition-all"
            :class="form.task_type === t.value ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-500'"
          >
            {{ t.label }}
          </button>
        </div>

        <!-- 平台选择 -->
        <label class="block text-sm font-medium text-gray-600 mb-2">选择平台（可多选）</label>
        <div class="flex flex-wrap gap-2 mb-4">
          <button
            v-for="p in availablePlatforms"
            :key="p.value"
            @click="togglePlatform(p.value)"
            class="px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all"
            :class="form.platforms.includes(p.value) ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-500'"
          >
            {{ p.label }}
          </button>
        </div>

        <!-- 采集数量 -->
        <label class="block text-sm font-medium text-gray-600 mb-1">每平台采集数量</label>
        <input v-model.number="form.count_per_platform" type="number" min="5" max="100" class="input-field mb-6" />

        <p v-if="error" class="text-red-500 text-sm mb-4">{{ error }}</p>

        <div class="flex gap-3">
          <button @click="showCreate = false" class="btn-secondary flex-1">取消</button>
          <button @click="createTask" class="btn-primary flex-1" :disabled="creating">
            {{ creating ? '创建中...' : '🚀 开始采集' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { taskApi } from '../api'

const router = useRouter()
const tasks = ref<any[]>([])
const showCreate = ref(false)
const creating = ref(false)
const error = ref('')

const form = reactive({
  keyword: '',
  task_type: 'product_group',
  platforms: [] as string[],
  count_per_platform: 20,
})

const taskTypes = [
  { value: 'product_group', label: '🛒 商品/团购' },
  { value: 'article_video', label: '📱 图文/视频' },
]

const allPlatforms = [
  { value: 'taobao', label: '🍑 淘宝' },
  { value: 'xiaohongshu', label: '📕 小红书' },
  { value: 'douyin', label: '🎵 抖音' },
  { value: 'meituan', label: '🍔 美团' },
  { value: 'amazon', label: '📦 亚马逊' },
]

const availablePlatforms = computed(() => {
  if (form.task_type === 'article_video') {
    return allPlatforms.filter(p => ['xiaohongshu', 'douyin'].includes(p.value))
  }
  return allPlatforms
})

function togglePlatform(p: string) {
  const idx = form.platforms.indexOf(p)
  if (idx >= 0) form.platforms.splice(idx, 1)
  else form.platforms.push(p)
}

async function createTask() {
  error.value = ''
  if (!form.keyword.trim()) { error.value = '请输入关键词'; return }
  if (form.platforms.length === 0) { error.value = '请至少选择一个平台'; return }

  creating.value = true
  try {
    await taskApi.create({
      keyword: form.keyword,
      task_type: form.task_type,
      platforms: form.platforms,
      count_per_platform: form.count_per_platform,
    })
    showCreate.value = false
    form.keyword = ''
    form.platforms = []
    await loadTasks()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '创建失败'
  }
  creating.value = false
}

async function loadTasks() {
  try {
    const res = await taskApi.list()
    tasks.value = res.data
  } catch {}
}

function viewData(taskId: number) {
  router.push(`/data/${taskId}`)
}

async function generateReport(taskId: number) {
  router.push(`/reports?task_id=${taskId}`)
}

async function cancelTask(id: number) {
  await taskApi.cancel(id)
  await loadTasks()
}

async function deleteTask(id: number) {
  if (confirm('确定删除此任务及所有数据？')) {
    await taskApi.delete(id)
    await loadTasks()
  }
}

function platformLabel(p: string) {
  const m: Record<string, string> = { taobao: '淘宝', xiaohongshu: '小红书', douyin: '抖音', meituan: '美团', amazon: '亚马逊' }
  return m[p] || p
}

function statusLabel(s: string) {
  const m: Record<string, string> = { queued: '⏳ 排队中', running: '🔄 采集中', completed: '✅ 已完成', failed: '❌ 失败', cancelled: '🚫 已取消' }
  return m[s] || s
}

function statusBadge(s: string) {
  const m: Record<string, string> = { queued: 'badge badge-warning', running: 'badge badge-info', completed: 'badge badge-success', failed: 'badge badge-error', cancelled: 'badge' }
  return m[s] || 'badge'
}

function formatTime(t: string) {
  if (!t) return '-'
  const d = new Date(t)
  const now = new Date()
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  return d.toLocaleDateString('zh-CN')
}

onMounted(loadTasks)
// 每 5 秒自动刷新任务状态
setInterval(loadTasks, 5000)
</script>
