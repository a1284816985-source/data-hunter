<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 顶部导航 -->
    <nav class="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-6 flex items-center justify-between h-14">
        <div class="flex items-center gap-8">
          <router-link to="/tasks" class="flex items-center gap-2 text-primary-700 font-bold text-lg no-underline">
            <span>🔍</span> 数据猎手
          </router-link>
          <div class="flex gap-1">
            <router-link
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              :class="isActive(item.path) ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'"
            >
              {{ item.label }}
            </router-link>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-sm text-gray-400">{{ username || '未登录' }}</span>
          <button @click="showLogin = true" class="btn-secondary text-sm !px-3 !py-1.5" v-if="!username">登录</button>
          <button @click="logout" class="text-sm text-gray-400 hover:text-red-500" v-else>退出</button>
        </div>
      </div>
    </nav>

    <!-- 登录弹窗 -->
    <div v-if="showLogin" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showLogin = false">
      <div class="bg-white rounded-xl shadow-xl p-8 w-96">
        <h2 class="text-xl font-bold mb-6">登录</h2>
        <input v-model="loginForm.username" class="input-field mb-3" placeholder="用户名" @keyup.enter="doLogin" />
        <input v-model="loginForm.password" class="input-field mb-4" placeholder="密码" type="password" @keyup.enter="doLogin" />
        <p v-if="loginError" class="text-red-500 text-sm mb-3">{{ loginError }}</p>
        <div class="flex gap-3">
          <button @click="doLogin" class="btn-primary flex-1">登录</button>
          <button @click="doRegister" class="btn-secondary flex-1">注册</button>
        </div>
      </div>
    </div>

    <!-- 主内容 -->
    <main>
      <router-view :key="$route.fullPath" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from './api'

const route = useRoute()
const router = useRouter()

const username = ref('')
const showLogin = ref(false)
const loginError = ref('')
const loginForm = ref({ username: '', password: '' })

const navItems = [
  { label: '🔍 采集任务', path: '/tasks' },
  { label: '📊 数据浏览', path: '/data' },
  { label: '🤖 AI 报告', path: '/reports' },
  { label: '⚙️ 系统设置', path: '/settings' },
]

function isActive(path: string) {
  return route.path.startsWith(path)
}

async function doLogin() {
  try {
    loginError.value = ''
    const res = await authApi.login(loginForm.value.username, loginForm.value.password)
    localStorage.setItem('token', res.data.token)
    username.value = res.data.username
    showLogin.value = false
  } catch (e: any) {
    loginError.value = e.response?.data?.detail || '登录失败'
  }
}

async function doRegister() {
  try {
    loginError.value = ''
    await authApi.register(loginForm.value.username, loginForm.value.password)
    await doLogin()
  } catch (e: any) {
    loginError.value = e.response?.data?.detail || '注册失败'
  }
}

function logout() {
  localStorage.removeItem('token')
  username.value = ''
}

onMounted(async () => {
  const token = localStorage.getItem('token')
  if (token) {
    try {
      const res = await authApi.me()
      username.value = '用户' + res.data.user_id
    } catch {
      localStorage.removeItem('token')
    }
  }
})
</script>
