import { createApp, defineAsyncComponent } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './assets/global.css'
import './assets/theme.css'
import 'highlight.js/styles/github-dark.css'  // 代码高亮样式
import 'katex/dist/katex.min.css'  // KaTeX 数学公式样式
import './utils/toast'
import i18n from './composables/useI18n'
import { getStoredToken, getCachedAuthProvider } from './api/auth'

import { configure } from "vue-gtag";

const HomePage = () => import('./pages/HomePage.vue')
const ChatPage = () => import('./pages/ChatPage.vue')
const SkillsPage = () => import('./pages/SkillsPage.vue')
const SkillDetailPage = () => import('@/pages/SkillDetailPage.vue')
const ToolsPage = () => import('./pages/ToolsPage.vue')
const ToolDetailPage = () => import('./pages/ToolDetailPage.vue')
const ScienceToolDetail = () => import('./pages/ScienceToolDetail.vue')
const TasksPage = () => import('./pages/TasksPage.vue')
const LoginPage = () => import('./pages/LoginPage.vue')
const MainLayout = () => import('./pages/MainLayout.vue')
const SharePage = () => import('./pages/SharePage.vue')
const ShareLayout = () => import('./pages/ShareLayout.vue')

configure({
  tagId: 'G-XCRZ3HH31S' // Replace with your own Google Analytics tag ID
})

// Create router
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { 
      path: '/chat', 
      component: MainLayout,
      meta: { requiresAuth: true },
      children: [
        { 
          path: '', 
          component: HomePage, 
          alias: ['/', '/home'],
          meta: { requiresAuth: true }
        },
        { 
          path: ':sessionId', 
          component: ChatPage,
          meta: { requiresAuth: true }
        },
        { 
          path: 'skills', 
          component: SkillsPage,
          meta: { requiresAuth: true }
        },
        { 
          path: 'skills/:skillName', 
          component: SkillDetailPage,
          meta: { requiresAuth: true }
        },
        { 
          path: 'tools', 
          component: ToolsPage,
          meta: { requiresAuth: true }
        },
        { 
          path: 'tools/:toolName', 
          component: ToolDetailPage,
          meta: { requiresAuth: true }
        },
        {
          path: 'science-tools/:toolName',
          component: ScienceToolDetail,
          meta: { requiresAuth: true }
        },
        {
          path: 'tasks',
          component: TasksPage,
          meta: { requiresAuth: true }
        }
      ]
    },
    {
      path: '/share',
      component: ShareLayout,
      children: [
        {
          path: ':sessionId',
          component: SharePage,
        }
      ]
    },
    { 
      path: '/login', 
      component: LoginPage
    }
  ]
})

// Global route guard
router.beforeEach(async (to, _, next) => {
  const requiresAuth = to.matched.some((record: any) => record.meta?.requiresAuth)
  const hasToken = !!getStoredToken()
  
  if (requiresAuth) {
    const authProvider = await getCachedAuthProvider()
    
    if (authProvider === 'none') {
      next()
      return
    }
    
    if (!hasToken) {
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
      return
    }
  }
  
  if (to.path === '/login' && hasToken) {
    next('/')
  } else {
    next()
  }
})

const app = createApp(App)

app.component('molecule-viewer', defineAsyncComponent(() => import('./components/MoleculeViewer.vue')))

app.use(router)
app.use(i18n)
app.mount('#app')
