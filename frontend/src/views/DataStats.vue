<template>
  <div class="page-container">
    <div class="stats-header">
      <div class="header-info">
        <h1 class="page-title">数据统计</h1>
        <p class="page-subtitle">事项完成情况与部门响应率分析</p>
      </div>
      <el-button type="success" size="large" class="export-btn" @click="exportToExcel">
        <el-icon><Download /></el-icon> 导出 Excel 报告
      </el-button>
    </div>

    <el-row :gutter="24" class="top-stats">
      <el-col :span="8">
        <el-card class="stat-mini-card">
          <div class="mini-icon blue"><Document /></div>
          <div class="mini-data">
            <span class="mini-label">累计事项数</span>
            <span class="mini-value">{{ statsData.total_items }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-mini-card">
          <div class="mini-icon purple"><User /></div>
          <div class="mini-data">
            <span class="mini-label">总反馈人次</span>
            <span class="mini-value">{{ statsData.total_feedbacks }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-mini-card">
          <div class="mini-icon green"><DataLine /></div>
          <div class="mini-data">
            <span class="mini-label">总完成响应率</span>
            <span class="mini-value">{{ statsData.completion_rate }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>


    <el-row :gutter="24">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header><span class="card-title">近期事项反馈对比 (Top 7)</span></template>
          <div class="chart-container" v-if="statsData.item_comparison && statsData.item_comparison.length">
             <div class="bar-group" v-for="item in statsData.item_comparison" :key="item.id">
                <div class="bar-label" :title="item.title">{{ item.title }}</div>
                <div class="bar-track">
                   <div class="bar-fill blue-fill" :style="{ width: item.rate + '%' }"></div>
                </div>
                <div class="bar-value">{{ item.rate }}%</div>
             </div>
          </div>
          <div class="chart-placeholder" v-else>
            <el-empty description="暂无图表数据" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header><span class="card-title">各部门反应速率排行</span></template>
          <div class="chart-container" v-if="statsData.dept_ranking && statsData.dept_ranking.length">
             <div class="rank-list">
                <div class="rank-item" v-for="(dept, idx) in statsData.dept_ranking" :key="idx">
                   <div class="rank-index" :class="{ 'top-3': idx < 3 }">{{ idx + 1 }}</div>
                   <div class="rank-info">
                      <div class="rank-name">{{ dept.name }}</div>
                      <div class="rank-bar-bg">
                         <div class="rank-bar-fill green-fill" :style="{ width: dept.rate + '%' }"></div>
                      </div>
                   </div>
                   <div class="rank-rate">{{ dept.rate }}%</div>
                </div>
             </div>
          </div>
          <div class="chart-placeholder" v-else>
            <el-empty description="暂无排行数据" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import apiClient from '../api'
import { Download, Document, User, DataLine } from '@element-plus/icons-vue'

const items = ref([])
// 统计数据状态对象
const statsData = ref({
    total_items: 0,
    total_feedbacks: 0,
    completion_rate: '0%',
    item_comparison: [], // 用于存储 Top 7 事项对比数据
    dept_ranking: []     // 用于存储部门响应排行数据
})

onMounted(async () => {
    try {
        const res = await apiClient.get('/items/stats/summary')
        statsData.value = res.data
    } catch (e) {
        console.error("Failed to load stats", e)
    }
})

async function exportToExcel() {
    try {
        const res = await apiClient.get('/items', { params: { limit: 100000 } })
        const allItems = res.data.items || []
        const headers = ['ID', '事项标题', '创建人ID', '状态', '截止时间', '附件数']
        let csvContent = "\uFEFF" + headers.join(",") + "\n"
        allItems.forEach(item => {
            const row = [ item.id, item.title, item.creator_id, item.status, item.deadline, item.attachments ? JSON.parse(item.attachments).length : 0 ]
            csvContent += row.map(e => `"${e}"`).join(",") + "\n"
        })
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement("a")
        link.setAttribute("href", url)
        link.setAttribute("download", "data_stats_export.csv")
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    } catch (e) {
        alert("导出失败: " + e.message)
    }
}
</script>

<style scoped>
.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.page-title { font-size: 1.5rem; font-weight: 700; margin: 0 0 4px 0; }
.page-subtitle { color: #64748b; font-size: 0.875rem; }

.top-stats { margin-bottom: 2rem; }

.stat-mini-card {
  border: none !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
}

.stat-mini-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1.5rem;
}

.mini-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
}

.mini-icon.blue { background: #eff6ff; color: #3b82f6; }
.mini-icon.purple { background: #f5f3ff; color: #8b5cf6; }
.mini-icon.green { background: #f0fdf4; color: #22c55e; }

.mini-data { display: flex; flex-direction: column; }
.mini-label { font-size: 0.75rem; color: #64748b; }
.mini-value { font-size: 1.5rem; font-weight: 700; color: #1e293b; }

.chart-card { height: 100%; min-height: 480px; border: none !important; }
.card-title { font-weight: 600; font-size: 0.875rem; }
.chart-placeholder { height: 300px; display: flex; align-items: center; justify-content: center; }

/* Custom Bar Chart Styles */
.chart-container {
    padding: 1rem 0;
}

.bar-group {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
}

.bar-label {
    width: 120px;
    font-size: 0.875rem;
    color: #475569;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-align: right;
}

.bar-track {
    flex: 1;
    height: 10px;
    background: #f1f5f9;
    border-radius: 5px;
    overflow: hidden;
}

.bar-fill {
    height: 100%;
    border-radius: 5px;
    transition: width 1s ease;
}

.blue-fill { background: #3b82f6; }
.green-fill { background: #22c55e; }

.bar-value {
    width: 40px;
    font-size: 0.875rem;
    color: #64748b;
    font-weight: 600;
}

/* Rank List Styles */
.rank-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.rank-item {
    display: flex;
    align-items: center;
    gap: 12px;
}

.rank-index {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #f1f5f9;
    color: #64748b;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.75rem;
}

.rank-index.top-3 {
    background: #fffbeb;
    color: #d97706;
}

.rank-info {
    flex: 1;
}

.rank-name {
    font-size: 0.875rem;
    color: #1e293b;
    margin-bottom: 4px;
}

.rank-bar-bg {
    height: 6px;
    background: #f1f5f9;
    border-radius: 3px;
    overflow: hidden;
}

.rank-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 1s ease;
}

.rank-rate {
    width: 40px;
    text-align: right;
    font-size: 0.875rem;
    font-weight: 600;
    color: #475569;
}
</style>
