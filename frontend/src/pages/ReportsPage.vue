<template>
  <div class="page-container">
    <h1 class="text-2xl font-bold mb-6">AI 分析报告</h1>

    <!-- 报告列表 -->
    <div class="card mb-6">
      <h2 class="text-lg font-medium mb-4">历史报告</h2>
      <div v-if="reports.length === 0" class="text-gray-400 text-center py-8">暂无报告</div>
      <div v-for="r in reports" :key="r.id" class="flex items-center justify-between py-3 border-b last:border-0 cursor-pointer hover:bg-gray-50 px-2 rounded"
        @click="loadReport(r.id)">
        <div>
          <span class="font-medium">{{ r.title }}</span>
          <span class="text-xs text-gray-400 ml-3">{{ formatTime(r.created_at) }}</span>
        </div>
        <div class="flex gap-2">
          <span class="badge" :class="r.report_type === 'product_group' ? 'badge-info' : 'badge-warning'">
            {{ r.report_type === 'product_group' ? '商品/团购' : '图文/视频' }}
          </span>
          <button @click.stop="deleteReport(r.id)" class="text-red-400 text-sm hover:text-red-600">删除</button>
        </div>
      </div>
    </div>

    <!-- 生成新报告 -->
    <div class="card mb-6" v-if="!currentReport">
      <h2 class="text-lg font-medium mb-4">生成新报告</h2>
      <div class="flex gap-3 items-end">
        <div class="flex-1">
          <label class="block text-sm text-gray-500 mb-1">选择已完成的任务</label>
          <select v-model="selectedTaskId" class="input-field">
            <option :value="0">-- 选择任务 --</option>
            <option v-for="t in completedTasks" :key="t.id" :value="t.id">
              {{ t.keyword }} ({{ t.task_type === 'product_group' ? '商品/团购' : '图文/视频' }} | {{ t.total_items }}条)
            </option>
          </select>
        </div>
        <button @click="generateReport" class="btn-primary" :disabled="!selectedTaskId || generating">
          {{ generating ? '生成中...' : '🤖 生成报告' }}
        </button>
      </div>
    </div>

    <!-- 报告详情 -->
    <div v-if="currentReport">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-bold">{{ currentReport.title }}</h2>
        <button @click="currentReport = null" class="btn-secondary">← 返回列表</button>
      </div>

      <div v-for="(section, idx) in (currentReport.content?.sections || [])" :key="idx" class="card mb-4">
        <h3 class="text-lg font-medium mb-3">
          {{ idx === 0 ? '📊' : idx === 1 ? '📈' : idx === 2 ? '💬' : '🎯' }}
          {{ section.title }}
        </h3>

        <!-- 图表区域 -->
        <div v-if="section.chart_type !== 'none'" class="mb-4 bg-gray-50 rounded-lg p-4">
          <canvas :ref="(el: any) => setChartRef(idx, el)" class="w-full" style="max-height: 300px"></canvas>
        </div>

        <!-- 分析文字 -->
        <div class="prose prose-sm max-w-none text-gray-700" v-html="formatContent(section.content)"></div>
      </div>

      <!-- 总结 -->
      <div v-if="currentReport.content?.summary" class="card bg-primary-50 border-primary-100">
        <h3 class="text-lg font-medium mb-2">📌 总结</h3>
        <p class="text-gray-700">{{ currentReport.content.summary }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { reportApi, taskApi } from '../api'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const route = useRoute()
const reports = ref<any[]>([])
const completedTasks = ref<any[]>([])
const selectedTaskId = ref(0)
const generating = ref(false)
const currentReport = ref<any>(null)
const chartRefs = ref<Record<number, any>>({})
const chartInstances = ref<Chart[]>([])

function setChartRef(idx: number, el: any) {
  if (el) chartRefs.value[idx] = el
}

function formatTime(t: string) {
  if (!t) return ''
  return new Date(t).toLocaleDateString('zh-CN')
}

function formatContent(text: string) {
  if (!text) return ''
  return text.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

async function loadReports() {
  try {
    const res = await reportApi.list()
    reports.value = res.data
  } catch {}
}

async function loadCompletedTasks() {
  try {
    const res = await taskApi.list()
    completedTasks.value = res.data.filter((t: any) => t.status === 'completed')
  } catch {}
}

async function loadReport(id: number) {
  try {
    const res = await reportApi.get(id)
    currentReport.value = res.data
    await nextTick()
    renderCharts()
  } catch {}
}

function renderCharts() {
  // 清除旧图表
  chartInstances.value.forEach(c => c.destroy())
  chartInstances.value = []

  const sections = currentReport.value?.content?.sections || []
  sections.forEach((section: any, idx: number) => {
    const el = chartRefs.value[idx]
    if (!el || !section.chart_data || section.chart_type === 'none') return

    try {
      const chartData = section.chart_data
      let chart: Chart

      if (section.chart_type === 'bar') {
        chart = new Chart(el, {
          type: 'bar',
          data: {
            labels: chartData.labels || [],
            datasets: [{
              label: chartData.label || '',
              data: chartData.values || [],
              backgroundColor: '#3b82f6',
            }],
          },
          options: { responsive: true, maintainAspectRatio: true },
        })
      } else if (section.chart_type === 'pie') {
        chart = new Chart(el, {
          type: 'pie',
          data: {
            labels: chartData.labels || [],
            datasets: [{
              data: chartData.values || [],
              backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
            }],
          },
          options: { responsive: true, maintainAspectRatio: true },
        })
      } else {
        chart = new Chart(el, {
          type: 'line',
          data: {
            labels: chartData.labels || [],
            datasets: [{
              label: chartData.label || '',
              data: chartData.values || [],
              borderColor: '#3b82f6',
              tension: 0.3,
            }],
          },
          options: { responsive: true, maintainAspectRatio: true },
        })
      }
      chartInstances.value.push(chart)
    } catch {}
  })
}

async function generateReport() {
  if (!selectedTaskId.value) return
  generating.value = true
  try {
    const res = await reportApi.generate(selectedTaskId.value)
    currentReport.value = res.data
    await loadReports()
    await nextTick()
    renderCharts()
  } catch (e: any) {
    alert('生成失败：' + (e.response?.data?.detail || e.message))
  }
  generating.value = false
}

async function deleteReport(id: number) {
  if (confirm('确定删除此报告？')) {
    await reportApi.delete(id)
    if (currentReport.value?.id === id) currentReport.value = null
    await loadReports()
  }
}

onMounted(() => {
  loadReports()
  loadCompletedTasks()
  const taskId = route.query.task_id
  if (taskId) selectedTaskId.value = Number(taskId)
})
</script>
