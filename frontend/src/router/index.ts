import { createRouter, createWebHashHistory } from 'vue-router'
import TasksPage from '../pages/TasksPage.vue'
import DataPage from '../pages/DataPage.vue'
import ReportsPage from '../pages/ReportsPage.vue'
import SettingsPage from '../pages/SettingsPage.vue'

const routes = [
  { path: '/', redirect: '/tasks' },
  { path: '/tasks', name: 'tasks', component: TasksPage },
  { path: '/data/:taskId?', name: 'data', component: DataPage },
  { path: '/reports', name: 'reports', component: ReportsPage },
  { path: '/settings', name: 'settings', component: SettingsPage },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
