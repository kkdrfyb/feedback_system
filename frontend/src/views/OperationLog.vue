<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">操作日志</h1>
        <p class="page-subtitle">记录系统内的核心操作行为</p>
      </div>
      <el-input 
        v-model="searchQuery" 
        placeholder="搜索操作人或动作..." 
        prefix-icon="Search" 
        style="width: 300px"
        clearable
      />
    </div>

    <el-card class="log-card">
      <el-table :data="logs" style="width: 100%" class="modern-table">
        <el-table-column prop="timestamp" label="操作时间" width="220">
          <template #default="scope">
            <div class="time-box">
              <el-icon><Clock /></el-icon>
              <span>{{ scope.row.timestamp }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="user_name" label="操作人" width="180">
          <template #default="scope">
            <el-link type="primary" :underline="false">
              <el-icon><User /></el-icon> {{ scope.row.user_name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="action" label="动作" width="200" />
        <el-table-column prop="target_id" label="目标 ID" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Search, Clock, User } from '@element-plus/icons-vue'
import apiClient from '../api'

const searchQuery = ref('')
const logs = ref([])
onMounted(async () => {
  try {
    const res = await apiClient.get('/operation_logs')
    logs.value = res.data
  } catch(e) {
    logs.value = []
  }
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.page-title { font-size: 1.5rem; font-weight: 700; margin: 0 0 4px 0; }
.page-subtitle { color: #64748b; font-size: 0.875rem; }

.log-card { border: none !important; box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important; }

.time-box { display: flex; align-items: center; gap: 8px; color: #64748b; font-size: 0.875rem; }
</style>
