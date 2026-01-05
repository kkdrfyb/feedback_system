<template>
  <div class="page-container narrow">
    <div class="page-header">
      <h1 class="page-title">待办任务</h1>
      <p class="page-subtitle">请按时完成以下反馈提交</p>
    </div>

    <div v-if="todos.length > 0" class="todo-list">
      <el-card v-for="todo in todos" :key="todo.id" class="todo-item-card" @click="$router.push('/feedback/' + todo.id)">
        <div class="todo-content">
          <div class="todo-main">
            <h3 class="todo-title">{{ todo.title }}</h3>
            <p class="todo-desc text-truncate">{{ todo.description || '无详细说明' }}</p>
          </div>
          <div class="todo-meta">
            <div class="meta-item">
              <el-icon><Timer /></el-icon>
              <span>截止: {{ formatTime(todo.deadline) }}</span>
            </div>
            <el-icon class="arrow-icon"><ArrowRight /></el-icon>
          </div>
        </div>
      </el-card>
    </div>

    <el-empty v-else description="暂无待反馈事项" :image-size="200" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import apiClient from '../api'
import { Timer, ArrowRight } from '@element-plus/icons-vue'

const todos = ref([])

onMounted(async () => {
    try {
        const userId = localStorage.getItem("user_id")
        const res = await apiClient.get('/todos', { params: { user_id: userId } })
        todos.value = res.data
    } catch (err) {
        console.error("加载待办失败", err)
    }
})

const formatTime = (time) => time ? time.replace('T', ' ').split('.')[0] : ''
</script>

<style scoped>
.page-container.narrow {
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: rgb(var(--text-main));
  margin: 0 0 0.5rem 0;
}

.page-subtitle {
  color: rgb(var(--text-muted));
  font-size: 0.875rem;
}

.todo-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.todo-item-card {
  cursor: pointer;
  transition: var(--transition);
}

.todo-item-card:hover {
  transform: translateX(8px);
  border-left: 4px solid rgb(var(--primary)) !important;
}

.todo-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.todo-main {
  flex: 1;
  padding-right: 2rem;
}

.todo-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.125rem;
  font-weight: 600;
}

.todo-desc {
  font-size: 0.875rem;
  color: rgb(var(--text-muted));
  margin: 0;
}

.todo-meta {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  color: rgb(var(--text-muted));
  font-size: 0.875rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.arrow-icon {
  font-size: 1.25rem;
  color: rgb(var(--border-color));
}

.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400px;
}
</style>
