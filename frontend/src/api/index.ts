import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截：添加 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.params = { ...config.params, token }
  }
  return config
})

// ── 任务 API ──
export const taskApi = {
  getPlatforms: (taskType?: string) => api.get('/tasks/platforms', { params: { task_type: taskType } }),
  create: (data: any) => api.post('/tasks/', data),
  list: () => api.get('/tasks/'),
  get: (id: number) => api.get(`/tasks/${id}`),
  cancel: (id: number) => api.post(`/tasks/${id}/cancel`),
  delete: (id: number) => api.delete(`/tasks/${id}`),
}

// ── 数据 API ──
export const dataApi = {
  getItems: (taskId: number, params?: any) => api.get(`/data/tasks/${taskId}/items`, { params }),
  getStats: (taskId: number) => api.get(`/data/tasks/${taskId}/stats`),
  getDetail: (itemId: number) => api.get(`/data/items/${itemId}`),
  exportExcel: (taskId: number) => api.post(`/data/tasks/${taskId}/export`),
}

// ── 报告 API ──
export const reportApi = {
  generate: (taskId: number) => api.post('/reports/generate', { task_id: taskId }),
  list: (taskId?: number) => api.get('/reports/list', { params: { task_id: taskId } }),
  get: (id: number) => api.get(`/reports/${id}`),
  delete: (id: number) => api.delete(`/reports/${id}`),
  rewrite: (data: any) => api.post('/reports/rewrite', data),
}

// ── 认证 API ──
export const authApi = {
  login: (username: string, password: string) => api.post('/auth/login', { username, password }),
  register: (username: string, password: string) => api.post('/auth/register', { username, password }),
  me: () => api.get('/auth/me'),
}

// ── 账号 API ──
export const accountApi = {
  list: () => api.get('/accounts/'),
  upsert: (platform: string, data: any) => api.post(`/accounts/${platform}`, data),
  delete: (id: number) => api.delete(`/accounts/${id}`),
}

export default api
