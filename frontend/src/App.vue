<template>
  <div class="app-wrapper">
    <el-container v-if="isLoggedIn" class="main-layout">
      <el-aside width="240px" class="aside-menu">
        <div class="logo-container">
          <div class="logo-box">
            <el-icon><Monitor /></el-icon>
          </div>
          <span class="logo-text">IFMS 系统</span>
        </div>
        
        <el-menu
          :default-active="activeRoute"
          router
          class="nav-menu"
          background-color="#0f172a"
          text-color="#94a3b8"
          active-text-color="#fff"
        >
          <el-menu-item index="/">
            <el-icon><Monitor /></el-icon>
            <span>工作台</span>
          </el-menu-item>
          <el-menu-item index="/item/create" v-if="isAdmin">
            <el-icon><CirclePlus /></el-icon>
            <span>新建事项</span>
          </el-menu-item>
          <el-menu-item index="/groups" v-if="isAdmin">
            <el-icon><Briefcase /></el-icon>
            <span>分组管理</span>
          </el-menu-item>
          <el-menu-item index="/stats">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据统计</span>
          </el-menu-item>
          <el-menu-item index="/logs" v-if="isAdmin">
            <el-icon><Clock /></el-icon>
            <span>操作日志</span>
          </el-menu-item>
          
          <el-menu-item index="/todo" v-if="!isAdmin">
            <el-icon><List /></el-icon>
            <span>待办反馈</span>
          </el-menu-item>
        </el-menu>

        <div class="aside-footer">
          <div class="user-profile">
            <el-avatar :size="32">{{ (userName || '管')[0].toUpperCase() }}</el-avatar>
            <div class="user-info">
              <p class="user-name">{{ userName }}</p>
              <p class="user-role">{{ roleText }}</p>
            </div>
          </div>
          <el-button link @click="logout" class="logout-btn">
            <el-icon><SwitchButton /></el-icon>
          </el-button>
        </div>
      </el-aside>
      
      <el-container class="content-container">
        <el-header height="60px" class="page-top-header">
          <div class="breadcrumb-container">
            <span class="breadcrumb-title">{{ pageTitle }}</span>
          </div>
        </el-header>
        <el-main class="main-body">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
    
    <div v-else class="auth-layout">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from './auth'
import { Monitor, CirclePlus, Briefcase, DataAnalysis, Clock, List, SwitchButton } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const { isLoggedIn, isAdmin, username: authUserName, clearSession } = useAuth()

const userName = computed(() => authUserName.value || '管理员')
const roleText = computed(() => isAdmin.value ? '系统开发/管理' : '职员')
const activeRoute = computed(() => route.path)

const pageTitle = computed(() => {
  const titles = {
    '/': '工作台',
    '/item/create': '新建事项',
    '/groups': '分组管理',
    '/stats': '数据统计',
    '/logs': '操作日志',
    '/todo': '待办反馈'
  }
  return titles[route.path] || '系统'
})

const logout = () => {
  clearSession()
  router.push('/login')
}
</script>

<style scoped>
.app-wrapper {
  height: 100vh;
  overflow: hidden;
}

.main-layout {
  height: 100%;
}

.aside-menu {
  background-color: #0f172a; /* Slate 900 */
  display: flex;
  flex-direction: column;
}

.logo-container {
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-box {
  width: 32px;
  height: 32px;
  background: white;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0f172a;
  font-size: 1.25rem;
}

.logo-text {
  font-size: 1.125rem;
  font-weight: 700;
  color: #fff;
}

.nav-menu {
  border-right: none;
  flex: 1;
}

:deep(.el-menu-item) {
  height: 50px;
  margin: 4px 12px;
  border-radius: 8px;
}

:deep(.el-menu-item.is-active) {
  background-color: #1e293b !important;
}

.aside-footer {
  padding: 20px;
  border-top: 1px solid #1e293b;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-info p {
  margin: 0;
  line-height: 1.2;
}

.user-name {
  color: #fff;
  font-size: 0.875rem;
  font-weight: 600;
}

.user-role {
  color: #64748b;
  font-size: 0.75rem;
}

.logout-btn {
  color: #64748b;
  font-size: 1.25rem;
}

.logout-btn:hover { color: #ef4444; }

.page-top-header {
  background: #fff;
  border-bottom: 1px solid rgb(var(--border-color));
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.breadcrumb-title {
  font-weight: 600;
  color: #1e293b;
}

.main-body {
  padding: 24px;
  background: #f8fafc;
}

.auth-layout {
  height: 100%;
}
</style>
