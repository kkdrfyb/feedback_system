<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">数据概览</h1>
      <p class="page-subtitle">实时监控事项反馈进度</p>
    </div>

    <el-row :gutter="24" class="stats-row">
      <el-col :span="6">
        <div class="stats-card">
          <div class="stats-icon blue"><Document /></div>
          <div class="stats-info">
            <span class="stats-label">总事项数</span>
            <span class="stats-value" v-if="!statsLoading">{{ stats.total_items }}</span>
            <el-icon v-else class="is-loading"><Loading /></el-icon>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stats-card">
          <div class="stats-icon green"><Timer /></div>
          <div class="stats-info">
            <span class="stats-label">总反馈数</span>
            <span class="stats-value" v-if="!statsLoading">{{ stats.total_feedbacks }}</span>
            <el-icon v-else class="is-loading"><Loading /></el-icon>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stats-card">
          <div class="stats-icon navy"><CircleCheck /></div>
          <div class="stats-info">
            <span class="stats-label">响应率</span>
            <span class="stats-value" v-if="!statsLoading">{{ stats.completion_rate }}</span>
            <el-icon v-else class="is-loading"><Loading /></el-icon>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">事项列表</span>
          <el-button type="primary" size="small" @click="$router.push('/item/create')" v-if="isAdmin">
            <el-icon><Plus /></el-icon> 发起新事项
          </el-button>
        </div>
      </template>
      <div class="filters">
        <el-form :inline="true" @submit.prevent>
          <el-form-item label="数据范围">
            <el-radio-group v-model="scope">
              <el-radio-button label="mine_created">我发起的</el-radio-button>
              <el-radio-button label="mine_assigned">我参与的</el-radio-button>
              <el-radio-button v-if="isAdmin" label="all">全部</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="标题">
            <el-input v-model="titleLike" placeholder="标题关键词" clearable />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="statusFilter" placeholder="全部" clearable style="width: 140px">
              <el-option label="进行中" value="ongoing" />
              <el-option label="已完成" value="finished" />
            </el-select>
          </el-form-item>
          <el-form-item label="发起人">
            <el-input v-model="creatorName" placeholder="姓名包含" clearable />
          </el-form-item>
          <el-form-item label="参与人">
            <el-input v-model="participantName" placeholder="姓名包含" clearable />
          </el-form-item>
          <el-form-item label="发起日期">
            <el-date-picker
              v-model="createdRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>
          <el-form-item label="截止日期">
            <el-date-picker
              v-model="deadlineRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchItems">搜索</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
      <el-table 
        v-loading="loading"
        :data="items" 
        style="width: 100%" 
        class="modern-table"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="title" label="标题" min-width="150" sortable="custom" />
        <el-table-column prop="created_at" label="提出日期" width="180" sortable="custom">
          <template #default="scope">
             {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="deadline" label="截止日期" width="180" sortable="custom">
          <template #default="scope">
             {{ formatTime(scope.row.deadline) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" sortable="custom">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'ongoing' ? 'warning' : 'success'" effect="light" class="status-tag">
              {{ scope.row.status === 'ongoing' ? '进行中' : '已完成' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="$router.push('/item/detail/'+scope.row.id)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalItems"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import apiClient from '../api'
import { Document, CircleCheck, Timer, Plus, Calendar, Loading } from '@element-plus/icons-vue'

const items = ref([])
const loading = ref(false)
const statsLoading = ref(false)
const stats = ref({
    total_items: 0,
    total_feedbacks: 0,
    completion_rate: "0%"
})

// Pagination & Sorting
const currentPage = ref(1)
const pageSize = ref(20)
const totalItems = ref(0)
const sortBy = ref('created_at')
const sortOrder = ref('desc')
const scope = ref(localStorage.getItem('role') === 'admin' ? 'all' : 'mine_created')
const titleLike = ref('')
const statusFilter = ref('')
const creatorName = ref('')
const participantName = ref('')
const createdRange = ref([])
const deadlineRange = ref([])

const isAdmin = computed(() => localStorage.getItem('role') === 'admin')

const fetchStats = async () => {
    statsLoading.value = true
    try {
        const res = await apiClient.get('/items/stats/summary', {
            params: {
                scope: scope.value,
                user_id: Number(localStorage.getItem('user_id')),
                role: localStorage.getItem('role')
            }
        })
        stats.value = res.data
        totalItems.value = res.data.total_items 
    } catch (err) {
        console.error("加载统计失败", err)
    } finally {
        statsLoading.value = false
    }
}

const fetchItems = async () => {
    loading.value = true
    try {
        const res = await apiClient.get('/items', {
            params: {
                skip: (currentPage.value - 1) * pageSize.value,
                limit: pageSize.value,
                sort_by: sortBy.value,
                sort_order: sortOrder.value,
                scope: scope.value,
                user_id: Number(localStorage.getItem('user_id')),
                role: localStorage.getItem('role'),
                title_like: titleLike.value || undefined,
                status: statusFilter.value || undefined,
                creator_name: creatorName.value || undefined,
                participant_name: participantName.value || undefined,
                created_from: createdRange.value?.[0] || undefined,
                created_to: createdRange.value?.[1] || undefined,
                deadline_from: deadlineRange.value?.[0] || undefined,
                deadline_to: deadlineRange.value?.[1] || undefined
            }
        })
        items.value = res.data.items
        totalItems.value = res.data.total
    } catch (err) {
        console.error("加载列表失败", err)
    } finally {
        loading.value = false
    }
}

const handleSizeChange = (val) => {
    pageSize.value = val
    fetchItems()
}

const handleCurrentChange = (val) => {
    currentPage.value = val
    fetchItems()
}

const handleSortChange = ({ prop, order }) => {
    if (!order) {
        sortBy.value = 'created_at'
        sortOrder.value = 'desc'
    } else {
        sortBy.value = prop
        sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
    }
    fetchItems()
}

onMounted(() => {
    fetchStats()
    fetchItems()
})

const formatTime = (time) => time ? time.replace('T', ' ').split('.')[0] : ''
const resetFilters = () => {
    titleLike.value = ''
    statusFilter.value = ''
    creatorName.value = ''
    participantName.value = ''
    createdRange.value = []
    deadlineRange.value = []
    currentPage.value = 1
    fetchStats()
    fetchItems()
}
</script>

<style scoped>
.pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
}
/* ... existing styles ... */

<style scoped>
.page-container {
  max-width: 1200px;
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

.stats-row {
  margin-bottom: 2rem;
}
.filters {
  margin-bottom: 1rem;
}

.stats-card {
  background: #fff;
  padding: 1.5rem;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  gap: 1.25rem;
  box-shadow: var(--shadow);
  transition: var(--transition);
  height: 100%; /* Fix inconsistent size */
  cursor: pointer; /* Clickable */
}

.stats-card.active {
  border: 2px solid rgb(var(--primary));
  background-color: rgba(var(--primary), 0.05);
}

.stats-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.stats-icon {
  width: 56px;
  height: 56px;
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.stats-icon.blue { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.stats-icon.green { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
.stats-icon.navy { background: rgba(15, 23, 42, 0.1); color: #0f172a; }
.stats-icon.orange { background: rgba(249, 115, 22, 0.1); color: #f97316; }

.stats-info {
  display: flex;
  flex-direction: column;
}

.stats-label {
  font-size: 0.875rem;
  color: rgb(var(--text-muted));
}

.stats-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: rgb(var(--text-main));
}

.table-card {
  border-radius: var(--radius);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
}

.status-tag {
  border-radius: 20px;
  padding: 0 12px;
}

.modern-table :deep(.el-table__header) th {
  background-color: rgb(var(--bg-main)) !important;
  color: rgb(var(--text-muted));
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
</style>
