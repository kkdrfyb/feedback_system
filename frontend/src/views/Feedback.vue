<template>
  <div class="page-container narrow">
    <el-button link @click="$router.back()" class="back-btn">
      <el-icon><ArrowLeft /></el-icon> 返回待办列表
    </el-button>

    <div class="page-header">
      <h1 class="page-title">提交反馈反馈</h1>
      <p class="page-subtitle">针对“{{ item.title }}”提出你的宝贵意见</p>
    </div>

    <el-row :gutter="24">
      <el-col :span="16">
        <el-card class="feedback-card">
          <el-form label-position="top">
            <el-form-item label="反馈内容描述" required>
              <el-input 
                type="textarea" 
                v-model="content" 
                placeholder="请详细描述你的反馈点，包括现状、影响以及建议的解决方案..." 
                :rows="12"
                resize="none"
              />
            </el-form-item>
            <div class="form-actions">
              <el-button type="primary" @click="submitFeedback" size="large" :disabled="!content.trim()" class="submit-btn">
                确 认 提 交
              </el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="info-card">
          <template #header>
            <span class="info-title">事项详情</span>
          </template>
          <div class="info-item">
            <label>发起时间</label>
            <span>{{ formatTime(item.created_at) }}</span>
          </div>
          <div class="info-item">
            <label>截止时间</label>
            <span class="warning-text">{{ formatTime(item.deadline) }}</span>
          </div>
          <div class="info-item description">
            <label>事项描述</label>
            <p>{{ item.description || '暂无详细描述' }}</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import apiClient from '../api'
import { ArrowLeft } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const item = ref({})
const content = ref('')

onMounted(async () => {
    try {
        const id = route.params.itemId
        const res = await apiClient.get(`/items/${id}`)
        item.value = res.data.item
        // 注意：后端返回的结构可能需要调整，此时假设返回的是 item 相关信息
    } catch (err) {
        console.error("获取详情失败", err)
    }
})

async function submitFeedback() {
    try {
        // 后端需要 item_user_id，从获取到的事项中提取
        const item_user_id = item.value.item_user_id 
        await apiClient.post('/feedbacks', { 
            item_user_id: item_user_id, 
            content: content.value 
        })
        router.push('/todo')
    } catch (err) {
        alert("提交失败: " + (err.response?.data?.detail || err.message))
    }
}

const formatTime = (time) => time ? time.replace('T', ' ').split('.')[0] : ''
</script>

<style scoped>
.page-container.narrow {
  max-width: 1000px;
  margin: 0 auto;
}

.back-btn {
  margin-bottom: 2rem;
  color: rgb(var(--text-muted));
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

.feedback-card {
  padding: 1.5rem;
}

.form-actions {
  margin-top: 2rem;
  text-align: right;
}

.submit-btn {
  width: 100%;
}

.info-title {
  font-weight: 600;
}

.info-item {
  margin-bottom: 1.5rem;
}

.info-item label {
  display: block;
  font-size: 0.75rem;
  color: rgb(var(--text-muted));
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.info-item span {
  font-weight: 500;
}

.info-item.description p {
  font-size: 0.875rem;
  line-height: 1.6;
  margin: 0;
  color: rgb(var(--text-muted));
}

.warning-text {
  color: #e6a23c;
}
</style>
