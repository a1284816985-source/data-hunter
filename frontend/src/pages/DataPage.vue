<template>
  <div class="page-container">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold">数据浏览</h1>
        <p class="text-gray-400 text-sm mt-1" v-if="taskId">任务 #{{ taskId }} 的采集结果</p>
      </div>
      <div class="flex gap-3" v-if="items.length > 0">
        <button @click="exportExcel" class="btn-secondary">📥 导出 Excel</button>
        <button @click="$router.push(`/reports?task_id=${taskId}`)" class="btn-primary">🤖 生成分析报告</button>
      </div>
    </div>

    <!-- 无任务选择时 -->
    <div v-if="!taskId" class="card text-center py-16">
      <p class="text-gray-400 text-lg mb-4">请先从采集任务中选择一个查看数据</p>
      <router-link to="/tasks" class="btn-primary inline-block no-underline">去采集任务</router-link>
    </div>

    <!-- 有数据时 -->
    <template v-else>
      <!-- 统计 -->
      <div class="card mb-6">
        <div class="flex items-center gap-6 flex-wrap">
          <div class="text-center">
            <div class="text-2xl font-bold text-primary-600">{{ stats.total_items }}</div>
            <div class="text-sm text-gray-400">总计</div>
          </div>
          <div v-for="s in stats.by_platform" :key="s.platform" class="text-center">
            <div class="text-xl font-bold">{{ s.count }}</div>
            <div class="text-sm text-gray-400">{{ platformLabel(s.platform) }}</div>
          </div>
          <div class="text-center" v-if="stats.avg_price > 0">
            <div class="text-xl font-bold text-green-600">¥{{ stats.avg_price }}</div>
            <div class="text-sm text-gray-400">均价</div>
          </div>
          <span class="text-sm text-gray-400 ml-auto">每 10 秒自动刷新</span>
        </div>
      </div>

      <!-- 筛选 -->
      <div class="flex gap-3 mb-4 flex-wrap">
        <select v-model="filterPlatform" class="input-field !w-auto">
          <option value="">全部平台</option>
          <option v-for="p in platforms" :key="p" :value="p">{{ platformLabel(p) }}</option>
        </select>
        <select v-model="sortBy" class="input-field !w-auto" v-if="isProduct">
          <option value="">默认排序</option>
          <option value="price_asc">价格从低到高</option>
          <option value="price_desc">价格从高到低</option>
          <option value="sales">销量优先</option>
        </select>
        <select v-model="sortBy" class="input-field !w-auto" v-else>
          <option value="">默认排序</option>
          <option value="likes">点赞最多</option>
        </select>
      </div>

      <!-- 商品/团购模式 -->
      <div v-if="isProduct" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <div v-for="item in items" :key="item.id" class="card hover:shadow-md transition-shadow cursor-pointer" @click="showDetail(item)">
          <div class="aspect-square bg-gray-100 rounded-lg mb-3 overflow-hidden">
            <img :src="proxyUrl(item.main_image) || 'https://placehold.co/300x300/e2e8f0/94a3b8?text=暂无图片'" class="w-full h-full object-cover" :alt="item.title"
                 referrerpolicy="no-referrer"
                 @error="(e) => { e.target.src = 'https://placehold.co/300x300/e2e8f0/94a3b8?text=暂无图片' }" />
          </div>
          <h3 class="font-medium text-sm line-clamp-2 mb-2">{{ item.title || '无标题' }}</h3>
          <div class="flex items-center justify-between">
            <span class="text-lg font-bold text-red-500">¥{{ item.price || '-' }}</span>
            <span class="text-xs text-gray-400">{{ item.sales || '' }}</span>
          </div>
          <div class="flex items-center justify-between mt-1">
            <span class="text-xs text-gray-400">{{ item.shop_name || '' }}</span>
            <span class="badge badge-info text-xs">{{ platformLabel(item.platform) }}</span>
          </div>
          <!-- 规格快览 -->
          <div v-if="getQuickSpecs(item).length > 0" class="mt-2 pt-2 border-t border-gray-100">
            <div v-for="s in getQuickSpecs(item).slice(0, 3)" :key="s[0]" class="flex text-xs">
              <span class="text-gray-400 w-16 flex-shrink-0 truncate">{{ s[0] }}</span>
              <span class="text-gray-600 truncate">{{ s[1] }}</span>
            </div>
          </div>
          <button v-if="item.source_url" @click="openPreview(item)"
             class="block w-full mt-2 text-center text-xs text-primary-600 hover:text-primary-700 border border-primary-200 rounded py-1">🔗 浏览原页</button>
        </div>
      </div>

      <!-- 图文/视频模式 -->
      <div v-else class="space-y-3">
        <div v-for="item in items" :key="item.id" class="card hover:shadow-md transition-shadow">
          <div class="flex gap-4">
            <div class="w-24 h-24 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
              <img :src="proxyUrl(item.cover_image) || 'https://placehold.co/200x200/e2e8f0/94a3b8?text=封面'" class="w-full h-full object-cover"
                   referrerpolicy="no-referrer"
                   @error="(e) => { e.target.src = 'https://placehold.co/200x200/e2e8f0/94a3b8?text=封面' }" />
            </div>
            <div class="flex-1 min-w-0">
              <h3 class="font-medium text-sm line-clamp-2 mb-1">{{ item.title || '无标题' }}</h3>
              <p class="text-xs text-gray-400 line-clamp-2 mb-2">{{ item.content_text || '' }}</p>
              <div class="flex items-center gap-4 text-xs text-gray-500">
                <span>👍 {{ item.likes || '-' }}</span>
                <span>💬 {{ item.comments_count || '-' }}</span>
                <span>⭐ {{ item.favorites || '-' }}</span>
                <span>{{ item.author_name || '' }}</span>
              </div>
            </div>
            <div class="flex flex-col gap-2 justify-center flex-shrink-0">
              <span class="badge badge-info text-xs">{{ platformLabel(item.platform) }}</span>
              <button @click="openRewrite(item)" class="text-xs text-primary-600 hover:underline">📝 爆款仿写</button>
              <button v-if="item.source_url" @click="openPreview(item)"
                 class="text-xs text-gray-500 hover:text-primary-600">🔗 浏览</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="loading" class="text-center py-12 text-gray-400">加载中...</div>
      <div v-else-if="items.length === 0" class="text-center py-12 text-gray-400">暂无采集数据</div>

      <!-- 分页 -->
      <div class="flex justify-center gap-2 mt-6" v-if="total > pageSize">
        <button v-for="p in totalPages" :key="p" @click="page = p" class="px-3 py-1 rounded text-sm"
          :class="p === page ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600'">{{ p }}</button>
      </div>
    </template>

    <!-- 详情弹窗 -->
    <div v-if="detailItem" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="detailItem = null">
      <div class="bg-white rounded-xl shadow-xl p-8 w-[600px] max-h-[80vh] overflow-y-auto">
        <h2 class="text-lg font-bold mb-4">{{ detailItem.title }}</h2>
        <img :src="proxyUrl(detailItem.main_image)" class="w-full rounded-lg mb-4" v-if="detailItem.main_image"
             referrerpolicy="no-referrer"
             @error="(e) => { e.target.style.display = 'none' }" />
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><span class="text-gray-400">价格：</span><span class="font-bold text-red-500">¥{{ detailItem.price }}</span></div>
          <div><span class="text-gray-400">原价：</span>¥{{ detailItem.original_price || '-' }}</div>
          <div><span class="text-gray-400">销量：</span>{{ detailItem.sales || '-' }}</div>
          <div><span class="text-gray-400">评分：</span>{{ detailItem.rating || '-' }}</div>
          <div><span class="text-gray-400">店铺：</span>{{ detailItem.shop_name || '-' }}</div>
          <div><span class="text-gray-400">平台：</span>{{ platformLabel(detailItem.platform) }}</div>
        </div>
        <a v-if="detailItem.source_url" :href="detailItem.source_url" target="_blank" class="text-primary-600 text-sm mt-4 inline-block">查看原文 →</a>
        <button @click="detailItem = null" class="btn-secondary w-full mt-4">关闭</button>
      </div>
    </div>

    <!-- 页面预览弹窗 -->
    <div v-if="previewItem" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" @click.self="previewItem = null">
      <div class="bg-white rounded-xl shadow-xl w-[700px] max-h-[85vh] overflow-y-auto">
        <!-- 顶部操作栏 -->
        <div class="sticky top-0 bg-white border-b px-6 py-3 flex items-center justify-between z-10 rounded-t-xl">
          <span class="font-medium text-sm">{{ platformLabel(previewItem.platform) }} · 商品详情</span>
          <div class="flex gap-2">
            <a :href="previewItem.source_url" target="_blank" rel="noreferrer noopener" class="btn-primary text-xs !px-3 !py-1.5">↗ 打开原页面</a>
            <button @click="previewItem = null" class="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
          </div>
        </div>
        
        <!-- 内容区 -->
        <div class="p-6">
          <!-- 商品图片画廊 -->
          <div v-if="isProduct && allPreviewImages.length > 0" class="mb-4">
            <img :src="proxyUrl(allPreviewImages[activeImgIdx])" 
                 class="w-full max-h-80 object-contain rounded-lg bg-gray-50"
                 referrerpolicy="no-referrer"
                 @error="(e) => { e.target.style.display = 'none' }" />
            <div v-if="allPreviewImages.length > 1" class="flex gap-2 mt-2 overflow-x-auto pb-2">
              <img v-for="(img, i) in allPreviewImages" :key="i"
                   :src="proxyUrl(img)" @click="activeImgIdx = i"
                   class="w-16 h-16 object-cover rounded border-2 cursor-pointer flex-shrink-0"
                   :class="i === activeImgIdx ? 'border-primary-500' : 'border-gray-200'"
                   referrerpolicy="no-referrer"
                   @error="(e) => { e.target.style.display = 'none' }" />
            </div>
          </div>
          <img v-else-if="!isProduct" :src="proxyUrl(previewItem.cover_image)"
               class="w-full max-h-80 object-contain rounded-lg mb-4 bg-gray-50"
               referrerpolicy="no-referrer"
               @error="(e) => { e.target.style.display = 'none' }" />
          
          <!-- 标题 -->
          <h2 class="text-lg font-bold mb-4">{{ previewItem.title }}</h2>
          
          <!-- 商品模式字段 -->
          <div v-if="isProduct" class="grid grid-cols-3 gap-3 mb-4">
            <div class="bg-gray-50 rounded-lg p-3 text-center">
              <div class="text-2xl font-bold text-red-500">¥{{ previewItem.price || '-' }}</div>
              <div class="text-xs text-gray-400">价格</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-3 text-center">
              <div class="text-lg font-bold">{{ previewItem.sales || '-' }}</div>
              <div class="text-xs text-gray-400">销量</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-3 text-center">
              <div class="text-lg font-bold">{{ previewItem.rating || '-' }}</div>
              <div class="text-xs text-gray-400">评分</div>
            </div>
          </div>
          
          <!-- 图文模式字段 -->
          <div v-else class="flex gap-4 mb-4">
            <div class="bg-gray-50 rounded-lg p-3 text-center flex-1">
              <div class="text-lg font-bold">{{ previewItem.likes || '-' }}</div>
              <div class="text-xs text-gray-400">👍 点赞</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-3 text-center flex-1">
              <div class="text-lg font-bold">{{ previewItem.comments_count || '-' }}</div>
              <div class="text-xs text-gray-400">💬 评论</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-3 text-center flex-1">
              <div class="text-lg font-bold">{{ previewItem.favorites || '-' }}</div>
              <div class="text-xs text-gray-400">⭐ 收藏</div>
            </div>
          </div>
          
          <!-- 正文内容 -->
          <div class="bg-gray-50 rounded-lg p-4 mb-4">
            <p class="text-sm text-gray-700 whitespace-pre-wrap" v-if="previewItem.content_text">{{ previewItem.content_text }}</p>
            <p class="text-sm text-gray-400" v-else>
              📱 该内容为{{ platformLabel(previewItem.platform) }}平台采集，<br>
              正文需点击「↗ 打开原页面」查看。
            </p>
          </div>
          
          <!-- 标签 -->
          <div v-if="previewItem.tags && previewItem.tags.length" class="flex flex-wrap gap-1 mb-4">
            <span v-for="tag in previewItem.tags" :key="tag" class="badge badge-info text-xs">#{{ tag }}</span>
          </div>

          <!-- 规格参数 -->
          <div v-if="specEntries.length > 0" class="mb-4">
            <h4 class="text-sm font-medium text-gray-500 mb-2">📋 商品参数</h4>
            <div class="bg-gray-50 rounded-lg divide-y">
              <div v-for="(v, k) in specEntries.slice(0, 15)" :key="k" class="flex px-3 py-2 text-sm">
                <span class="text-gray-400 w-32 flex-shrink-0">{{ k }}</span>
                <span class="text-gray-700">{{ v }}</span>
              </div>
            </div>
          </div>
          
          <!-- 元信息 -->
          <div class="text-xs text-gray-400 space-y-1">
            <div v-if="previewItem.shop_name">店铺：{{ previewItem.shop_name }}</div>
            <div v-if="previewItem.author_name">作者：{{ previewItem.author_name }}</div>
            <div v-if="previewItem.publish_time">发布时间：{{ previewItem.publish_time }}</div>
            <div v-if="previewItem.source_url" class="truncate">链接：{{ previewItem.source_url }}</div>
          </div>

          <!-- 情感分析 -->
          <div class="mt-4 pt-4 border-t">
            <button @click="doSentiment(previewItem.id)" 
                    class="btn-primary text-sm w-full" 
                    :disabled="sentimentLoading">
              {{ sentimentLoading ? '🤖 AI分析中...' : (sentimentResult ? '🔄 重新分析' : '🤖 AI 情感分析') }}
            </button>
            <div v-if="sentimentResult" class="mt-3 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-lg">{{ sentimentResult.sentiment === 'positive' ? '😊' : sentimentResult.sentiment === 'negative' ? '😟' : '😐' }}</span>
                <span class="font-bold">{{ sentimentResult.summary }}</span>
                <span class="badge" :class="sentimentResult.sentiment === 'positive' ? 'badge-success' : sentimentResult.sentiment === 'negative' ? 'badge-error' : 'badge-warning'">
                  情感分 {{ sentimentResult.score }}
                </span>
              </div>
              <div v-if="sentimentResult.pros?.length" class="text-sm text-green-700 mb-1">✅ {{ sentimentResult.pros.join('；') }}</div>
              <div v-if="sentimentResult.cons?.length" class="text-sm text-red-600 mb-1">⚠️ {{ sentimentResult.cons.join('；') }}</div>
              <div class="text-xs text-gray-500 mt-2">
                <span v-if="sentimentResult.buy_advice">💡 {{ sentimentResult.buy_advice }}</span>
                <span v-if="sentimentResult.target_users" class="ml-3">👥 {{ sentimentResult.target_users }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 爆款仿写弹窗 -->
    <div v-if="rewriteItem" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="rewriteItem = null">
      <div class="bg-white rounded-xl shadow-xl p-8 w-[560px] max-h-[85vh] overflow-y-auto">
        <h2 class="text-xl font-bold mb-4">📝 爆款仿写</h2>
        <div class="bg-gray-50 rounded-lg p-4 mb-4 text-sm">
          <p class="text-gray-400 mb-1">参考原文：</p>
          <p class="font-medium">{{ rewriteItem.title }}</p>
          <p class="text-gray-500 mt-2 line-clamp-4">{{ rewriteItem.content_text }}</p>
        </div>
        <label class="block text-sm font-medium text-gray-600 mb-1">你的产品/主题</label>
        <input v-model="rewriteTopic" class="input-field mb-4" placeholder="如：粉底液" />
        <label class="block text-sm font-medium text-gray-600 mb-2">保留元素</label>
        <div class="flex gap-4 mb-4">
          <label class="flex items-center gap-2 text-sm"><input type="checkbox" v-model="keepStructure" /> 结构框架</label>
          <label class="flex items-center gap-2 text-sm"><input type="checkbox" v-model="keepTone" /> 语气风格</label>
          <label class="flex items-center gap-2 text-sm"><input type="checkbox" v-model="keepHook" /> 开头钩子</label>
        </div>

        <!-- 仿写结果 -->
        <div v-if="rewriteResult" class="bg-green-50 rounded-lg p-4 mb-4">
          <p class="text-sm font-medium text-green-700 mb-2">📌 建议标题</p>
          <p class="text-sm mb-3">{{ rewriteResult.title }}</p>
          <p class="text-sm font-medium text-green-700 mb-2">📝 正文文案</p>
          <p class="text-sm whitespace-pre-wrap mb-3">{{ rewriteResult.content }}</p>
          <p class="text-sm font-medium text-green-700 mb-2">🏷 推荐话题</p>
          <div class="flex flex-wrap gap-1">
            <span v-for="tag in rewriteResult.tags" :key="tag" class="badge badge-info">#{{ tag }}</span>
          </div>
        </div>

        <div class="flex gap-3">
          <button @click="rewriteItem = null" class="btn-secondary flex-1">关闭</button>
          <button @click="doRewrite" class="btn-primary flex-1" :disabled="rewriting">
            {{ rewriting ? '生成中...' : (rewriteResult ? '🔄 换一版' : '✨ 开始仿写') }}
          </button>
          <button v-if="rewriteResult" @click="copyRewrite" class="btn-secondary">📋 复制</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { dataApi, reportApi } from '../api'
import axios from 'axios'

const route = useRoute()
const taskId = computed(() => Number(route.params.taskId) || 0)
const isProduct = ref(true)
const items = ref<any[]>([])
const stats = ref<any>({ total_items: 0, by_platform: [], avg_price: 0 })
const loading = ref(false)
const filterPlatform = ref('')
const sortBy = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const detailItem = ref<any>(null)
const rewriteItem = ref<any>(null)
const previewItem = ref<any>(null)
const rewriteTopic = ref('')
const rewriteResult = ref<any>(null)
const rewriting = ref(false)
const keepStructure = ref(true)
const keepTone = ref(true)
const keepHook = ref(true)
let timer: any = null

const totalPages = computed(() => Math.ceil(total.value / pageSize))
const platforms = computed(() => stats.value.by_platform?.map((p: any) => p.platform) || [])

function getQuickSpecs(item: any) {
  const specs = item?.specs
  if (!specs || typeof specs !== 'object' || Array.isArray(specs)) return []
  // Amazon 字段中英文映射
  const keyMap: Record<string, string> = {
    'Quantity': '数量', 'List Price': '定价', 'Color': '颜色', 'Size': '尺寸',
    'Brand': '品牌', 'Material': '材质', 'Weight': '重量', 'Dimensions': '尺寸',
    'Style': '款式', 'Shape': '形状', 'Pattern': '图案',
    'Item Weight': '重量', 'Package Dimensions': '包装尺寸',
    'Batteries': '电池', 'Power Source': '电源', 'Voltage': '电压',
    'Country of Origin': '产地', 'Manufacturer': '制造商',
    'Ships from': '发货地', 'Sold by': '卖家',
    'ASIN': 'ASIN', 'Date First Available': '上架日期',
    'Amazon.com Return Policy': '退货政策',
    'Customer Reviews': '用户评价', 'Best Sellers Rank': '热销排名',
    'Product Dimensions': '产品尺寸', 'Item model number': '型号',
    'Is Discontinued By Manufacturer': '停产状态',
  }
  return Object.entries(specs)
    .filter(([, v]) => {
      if (!v) return false
      const sv = String(v).toLowerCase()
      if (sv === '1' || sv === 'true' || sv === 'false') return false
      return true
    })
    .map(([k, v]) => [keyMap[k] || k, v])
}

function platformLabel(p: string) {
  const m: Record<string, string> = { taobao: '淘宝', xiaohongshu: '小红书', douyin: '抖音', meituan: '美团', amazon: '亚马逊' }
  return m[p] || p
}

async function loadItems() {
  if (!taskId.value) return
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize }
    if (filterPlatform.value) params.platform = filterPlatform.value
    if (sortBy.value) params.sort_by = sortBy.value

    const [itemsRes, statsRes] = await Promise.all([
      dataApi.getItems(taskId.value, params),
      dataApi.getStats(taskId.value),
    ])
    items.value = itemsRes.data.items
    total.value = itemsRes.data.total
    stats.value = statsRes.data

    // 判断模式
    if (items.value.length > 0) {
      isProduct.value = ['product', 'group_buy'].includes(items.value[0].item_type)
    }
  } catch {}
  loading.value = false
}

async function exportExcel() {
  try {
    const res = await dataApi.exportExcel(taskId.value)
    window.open('/api/data/download/' + res.data.filename, '_blank')
  } catch {}
}

function showDetail(item: any) {
  detailItem.value = item
}

function openPreview(item: any) {
  previewItem.value = item
  activeImgIdx.value = 0
  sentimentResult.value = null
}

const activeImgIdx = ref(0)
const sentimentLoading = ref(false)
const sentimentResult = ref<any>(null)

const allPreviewImages = computed(() => {
  if (!previewItem.value) return []
  const imgs = []
  if (previewItem.value.main_image) imgs.push(previewItem.value.main_image)
  if (previewItem.value.detail_images) {
    for (const img of previewItem.value.detail_images) {
      if (img && !imgs.includes(img)) imgs.push(img)
    }
  }
  return imgs
})

const specEntries = computed(() => {
  if (!previewItem.value?.specs) return []
  const specs = previewItem.value.specs
  if (typeof specs === 'object' && !Array.isArray(specs)) {
    const keyMap: Record<string, string> = {
      'Quantity': '数量', 'List Price': '定价', 'Color': '颜色', 'Size': '尺寸',
      'Brand': '品牌', 'Material': '材质', 'Weight': '重量', 'Dimensions': '尺寸',
      'Item Weight': '重量', 'Package Dimensions': '包装尺寸',
      'Ships from': '发货地', 'Sold by': '卖家',
      'Amazon.com Return Policy': '退货政策', 'Product Dimensions': '产品尺寸',
      'Item model number': '型号', 'Country of Origin': '产地',
    }
    return Object.entries(specs)
      .filter(([, v]) => v)
      .map(([k, v]) => [keyMap[k] || k, v])
  }
  return []
})

async function doSentiment(itemId: number) {
  sentimentLoading.value = true
  try {
    const res = await axios.post(`/api/reports/sentiment/${itemId}`)
    sentimentResult.value = res.data
  } catch (e: any) {
    alert('分析失败：' + (e.response?.data?.detail || e.message))
  }
  sentimentLoading.value = false
}

function openRewrite(item: any) {
  rewriteItem.value = item
  rewriteTopic.value = ''
  rewriteResult.value = null
}

async function doRewrite() {
  if (!rewriteTopic.value.trim()) return
  rewriting.value = true
  try {
    const res = await reportApi.rewrite({
      item_id: rewriteItem.value.id,
      own_product_topic: rewriteTopic.value,
      keep_structure: keepStructure.value,
      keep_tone: keepTone.value,
      keep_hook: keepHook.value,
    })
    rewriteResult.value = res.data
  } catch (e: any) {
    alert('仿写失败：' + (e.response?.data?.detail || e.message))
  }
  rewriting.value = false
}

async function copyRewrite() {
  if (!rewriteResult.value) return
  const text = `标题：${rewriteResult.value.title}\n\n${rewriteResult.value.content}\n\n话题：${(rewriteResult.value.tags || []).map((t: string) => '#' + t).join(' ')}`
  await navigator.clipboard.writeText(text)
  alert('已复制到剪贴板')
}

watch([taskId, page, filterPlatform, sortBy], () => loadItems())

// 图片代理：外部 CDN URL → 本地代理
const CDN_DOMAINS = ['xhscdn.com', 'alicdn.com', 'tbcdn.com', 'douyinstatic.com', 'pddpic.com']
function proxyUrl(url: string): string {
  if (!url || url.startsWith('/api/') || url.startsWith('data:') || url.startsWith('blob:')) return url
  if (url.includes('placehold.co')) return url
  const needsProxy = CDN_DOMAINS.some(d => url.includes(d))
  return needsProxy ? `/api/image-proxy?url=${encodeURIComponent(url)}` : url
}

onMounted(() => {
  loadItems()
  timer = setInterval(loadItems, 10000)
})

onUnmounted(() => clearInterval(timer))
</script>
