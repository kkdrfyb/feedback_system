<template>
  <div class="page-container narrow">
    <div class="page-header">
      <h1 class="page-title">发起反馈事项</h1>
      <p class="page-subtitle">指派相关人员提交反馈建议</p>
    </div>

    <el-card class="form-card">
      <el-form :model="form" label-position="top" class="modern-form">
        <el-form-item label="事项标题" required>
          <el-input v-model="form.title" placeholder="例如：2026年Q1产品满意度调查" size="large" />
        </el-form-item>
        
        <el-form-item label="详细说明">
          <el-input 
            type="textarea" 
            v-model="form.description" 
            placeholder="请详细描述反馈要求和目的..." 
            :rows="4" 
          />
        </el-form-item>

        <el-form-item label="附件模板">
           <el-upload
             v-model:file-list="fileList"
             action="#"
             multiple
             :auto-upload="false"
             :limit="5"
           >
             <el-button type="primary">点击上传附件</el-button>
             <template #tip>
               <div class="el-upload__tip">
                 支持多个文件上传，作为反馈模板供用户下载
               </div>
             </template>
           </el-upload>
        </el-form-item>

        <div class="form-row-full">
            <el-form-item label="截止时间" required>
              <el-date-picker
                v-model="form.deadline"
                type="datetime"
                placeholder="选择日期时间"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                size="large"
              />
            </el-form-item>
        </div>

        <div class="user-selector-area">
            <div class="area-label">选择参与人员 <span class="badge">{{ form.user_ids.length }}</span></div>
            <ThreeColUserSelector
                v-model="form.user_ids"
                :all-users="users"
                :custom-groups="customGroups"
            />
        </div>

        <div class="form-actions">
          <el-button @click="$router.back()">取消</el-button>
          <el-button type="primary" @click="createItem" class="submit-btn">立即发布</el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '../api'
import ThreeColUserSelector from '../components/ThreeColUserSelector.vue'

const router = useRouter()
const users = ref([])
const customGroups = ref([])

const form = ref({
    title: '',
    description: '',
    deadline: '',
    must_feedback: true,
    creator_id: parseInt(localStorage.getItem("user_id")),
    user_ids: []
})

const fileList = ref([])

onMounted(async () => {
    try {
        const userId = localStorage.getItem('user_id')
        const role = localStorage.getItem('role')
        
        const [uRes, gRes] = await Promise.all([
          apiClient.get('/users'),
          apiClient.get('/groups', { params: { user_id: userId, role: role } })
        ])
        users.value = uRes.data
        customGroups.value = gRes.data
    } catch (err) {
        console.error("数据初加载失败", err)
    }
})


async function createItem() {
    try {
        if (form.value.user_ids.length === 0) {
            alert("请至少选择一个参与人")
            return
        }

        const formData = new FormData()
        formData.append('title', form.value.title)
        formData.append('description', form.value.description || '')
        formData.append('deadline', form.value.deadline)
        formData.append('must_feedback', form.value.must_feedback)
        formData.append('creator_id', form.value.creator_id)
        formData.append('user_ids', JSON.stringify(form.value.user_ids))
        
        fileList.value.forEach(file => {
            formData.append('files', file.raw)
        })

        await apiClient.post("/items", formData)
        router.push("/")
    } catch (e) {
        alert("发布失败: " + (e.response?.data?.detail || e.message))
    }
}
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

.form-card {
  padding: 1rem;
}

.modern-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: rgb(var(--text-main));
  padding-bottom: 8px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgb(var(--border-color));
}

.submit-btn {
  padding-left: 2rem;
  padding-right: 2rem;
}

.user-selector-area {
  margin-top: 1rem;
}
.area-label {
    font-size: 14px;
    font-weight: 600;
    color: var(--el-text-color-regular);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.badge {
    background: var(--el-color-primary);
    color: #fff;
    padding: 0 8px;
    border-radius: 99px;
    font-size: 12px;
}
</style>
