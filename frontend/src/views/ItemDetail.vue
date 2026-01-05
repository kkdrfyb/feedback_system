<template>
  <div class="page-container">
    <el-button link @click="$router.push('/')" class="back-btn">
      <el-icon><ArrowLeft /></el-icon> 返回工作台
    </el-button>

    <div class="detail-header card-style">
      <div class="header-main">
        <h1 class="item-title">{{ item.title }}</h1>
        <div class="status-badge" :class="item.status">
          {{ item.status === 'ongoing' ? '进行中' : '已归档' }}
        </div>
      </div>
      <p class="item-desc">{{ item.description || '暂无详细描述' }}</p>

      <div class="attachment-box" v-if="item.attachments">
          <p class="attach-label">附件模板 ({{ attachmentsList.length }})</p>
          <div class="attach-list">
              <a v-for="(file, idx) in attachmentsList" :key="idx" :href="getDownloadUrl(file.path)" target="_blank" class="attach-item">
                  <el-icon><Document /></el-icon> {{ file.name }}
              </a>
          </div>
      </div>
      
      <div class="header-meta">
        <div class="meta-item">
          <label>截止日期</label>
          <span class="warning-text">{{ formatTime(item.deadline) }}</span>
        </div>
        <div class="meta-item">
          <label>完成进度</label>
          <span class="progress-text">{{ finishedCount }} / {{ feedbacks.length }} 已提交</span>
        </div>
      </div>
    </div>

    <el-card class="feedback-list-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">反馈列表</span>
          <el-button size="small" @click="exportData" v-if="isAdmin">
            <el-icon><Download /></el-icon> 导出数据
          </el-button>
        </div>
      </template>

      <el-table 
        v-loading="loading"
        :data="feedbacks" 
        style="width: 100%" 
        class="modern-table"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="user_name" label="参与人" width="120" sortable="custom">
          <template #default="scope">
            <span class="user-name-cell">{{ scope.row.user_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="反馈建议" min-width="300" sortable="custom">
          <template #default="scope">
            <div class="feedback-content-cell">
              {{ scope.row.content || '等待反馈中...' }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="last_feedback_time" label="反馈时间" width="180" sortable="custom">
          <template #default="scope">
            <span class="time-cell">{{ formatTime(scope.row.last_feedback_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" sortable="custom">
          <template #default="scope">
            <el-tag :type="scope.row.content ? 'success' : 'info'" size="small">
              {{ scope.row.content ? '已反馈' : '未反馈' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import apiClient from '../api'
import { ArrowLeft, Download, Document } from '@element-plus/icons-vue'

const route = useRoute()
const item = ref({})
const feedbacks = ref([])
const loading = ref(false)
const isAdmin = computed(() => localStorage.getItem('role') === 'admin')

const finishedCount = computed(() => feedbacks.value.filter(f => f.content).length)

const attachmentsList = computed(() => {
    if (!item.value.attachments) return []
    try {
        return JSON.parse(item.value.attachments)
    } catch (e) {
        return []
    }
})

const getDownloadUrl = (path) => {
    // path is like /api/uploads/xxx.pdf
    // we need full url
    return `${window.location.protocol}//${window.location.hostname}:8000${path}`
}

const handleSortChange = ({ prop, order }) => {
    if (!order) {
        // Reset to default sort (e.g. by time desc or original order)
        // Since we don't store original order, let's just sort by last_feedback_time desc as default
        feedbacks.value.sort((a, b) => {
             const tA = new Date(a.last_feedback_time || 0).getTime()
             const tB = new Date(b.last_feedback_time || 0).getTime()
             return tB - tA
        })
        return
    }
    
    feedbacks.value.sort((a, b) => {
        let valA = a[prop]
        let valB = b[prop]
        
        // Handle nulls
        if (valA === null || valA === undefined) valA = ''
        if (valB === null || valB === undefined) valB = ''
        
        if (prop === 'status') {
            // Sort by content existence
            valA = a.content ? 1 : 0
            valB = b.content ? 1 : 0
        }
        
        if (valA < valB) return order === 'ascending' ? -1 : 1
        if (valA > valB) return order === 'ascending' ? 1 : -1
        return 0
    })
}

onMounted(async () => {
    loading.value = true
    try {
        const id = route.params.id
        const res = await apiClient.get(`/items/${id}`)
        item.value = res.data.item
        feedbacks.value = res.data.feedbacks
        // Default sort: latest feedback first
        handleSortChange({}) 
    } catch (err) {
        console.error("加载详情失败", err)
    } finally {
        loading.value = false
    }
})

const formatTime = (time) => time ? time.replace('T', ' ').split('.')[0] : '-'

function exportData() {
    alert("导出功能开发中...")
}
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
}

.back-btn {
  margin-bottom: 2rem;
  color: rgb(var(--text-muted));
}

.card-style {
  background: #fff;
  border-radius: var(--radius);
  padding: 2rem;
  box-shadow: var(--shadow);
  margin-bottom: 2rem;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.item-title {
  font-size: 2rem;
  font-weight: 800;
  margin: 0;
  color: rgb(var(--text-main));
}

.status-badge {
  padding: 6px 16px;
  border-radius: 99px;
  font-size: 0.875rem;
  font-weight: 600;
}

.status-badge.ongoing { background: rgba(var(--primary), 0.1); color: rgb(var(--primary)); }
.status-badge.finished { background: rgba(103, 194, 58, 0.1); color: #67c23a; }

.item-desc {
  font-size: 1rem;
  color: rgb(var(--text-muted));
  line-height: 1.6;
  margin-bottom: 2rem;
}

.header-meta {
  display: flex;
  gap: 3rem;
  border-top: 1px solid rgb(var(--border-color));
  padding-top: 1.5rem;
}

.meta-item label {
  display: block;
  font-size: 0.75rem;
  color: rgb(var(--text-muted));
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.meta-item span {
  font-weight: 600;
}

.warning-text { color: #e6a23c; }
.progress-text { color: rgb(var(--primary)); }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
}

.user-name-cell {
  font-weight: 600;
  color: rgb(var(--text-main));
}

.feedback-content-cell {
  color: rgb(var(--text-muted));
  font-size: 0.875rem;
  line-height: 1.5;
}

.time-cell {
  font-size: 0.875rem;
  color: rgb(var(--text-muted));
}

.attachment-box {
    margin-bottom: 1.5rem;
    background: #f8fafc;
    padding: 1rem;
    border-radius: 8px;
}

.attach-label {
    font-size: 0.875rem;
    color: rgb(var(--text-muted));
    margin: 0 0 0.5rem 0;
    font-weight: 600;
}

.attach-list {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
}

.attach-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: #fff;
    border: 1px solid rgb(var(--border-color));
    border-radius: 4px;
    text-decoration: none;
    color: rgb(var(--primary));
    font-size: 0.875rem;
    transition: all 0.2s;
}

.attach-item:hover {
    border-color: rgb(var(--primary));
    background: rgba(var(--primary), 0.05);
}
</style>
