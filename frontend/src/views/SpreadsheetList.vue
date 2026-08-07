<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">表格协作</h1>
        <p class="page-subtitle">上传 Excel 模板，在线填写，自动保存，导出汇总</p>
      </div>
      <el-button type="primary" @click="showUpload = true">
        <el-icon><Plus /></el-icon> 上传新表格
      </el-button>
    </div>

    <el-table v-loading="loading" :data="sheets" style="width: 100%" class="modern-table">
      <el-table-column prop="title" label="表格名称" min-width="200" />
      <el-table-column prop="row_count" label="数据行数" width="120" />
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/spreadsheet/${row.id}`)">编辑</el-button>
          <el-button link type="success" @click="downloadExport(row)">导出</el-button>
          <el-button link type="danger" @click="deleteSheet(row)" v-if="canDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && sheets.length === 0" description="还没有表格，上传一个 Excel 开始吧" />

    <!-- 上传弹窗 -->
    <el-dialog v-model="showUpload" title="上传 Excel 模板" width="500px">
      <el-form label-position="top">
        <el-form-item label="表格名称">
          <el-input v-model="uploadTitle" placeholder="留空则使用文件名" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="uploadDesc" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
        <el-form-item label="负责人列（可选）">
          <el-input v-model="uploadOwner" placeholder="如 Excel 有「负责人」列，输入列名以实现行级权限" />
          <div class="el-upload__tip">Excel 第一行是列标题，其余行是数据。如果 Excel 包含「负责人」列，填写该列名称后，每行只能被对应的用户编辑</div>
        </el-form-item>
        <el-form-item label="Excel 文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".xlsx"
            :on-change="handleFileChange"
          >
            <el-button type="primary">选择文件</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" @click="doUpload" :loading="uploading">上传并创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import apiClient from '../api'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const sheets = ref([])
const loading = ref(false)
const showUpload = ref(false)
const uploadTitle = ref('')
const uploadDesc = ref('')
const uploadOwner = ref('')
const uploadFile = ref(null)
const uploading = ref(false)

const fetchSheets = async () => {
  loading.value = true
  try {
    const res = await apiClient.get('/spreadsheets')
    sheets.value = res.data
  } finally {
    loading.value = false
  }
}

const handleFileChange = (file) => {
  uploadFile.value = file.raw
}

const doUpload = async () => {
  if (!uploadFile.value) { ElMessage.warning('请选择 Excel 文件'); return }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', uploadFile.value)
    fd.append('title', uploadTitle.value)
    fd.append('description', uploadDesc.value)
    fd.append('owner_column', uploadOwner.value)
    await apiClient.post('/spreadsheets/upload', fd)
    ElMessage.success('上传成功')
    showUpload.value = false
    uploadFile.value = null
    uploadTitle.value = ''
    uploadDesc.value = ''
    uploadOwner.value = ''
    fetchSheets()
  } catch (e) {
    ElMessage.error('上传失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
}

const downloadExport = async (sheet) => {
  try {
    const res = await apiClient.get(`/spreadsheets/${sheet.id}/export`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url; a.download = `${sheet.title}_export.xlsx`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

const deleteSheet = async (sheet) => {
  try {
    await ElMessageBox.confirm('确定删除该表格？所有数据将被清除。', '确认', { type: 'warning' })
    await apiClient.delete(`/spreadsheets/${sheet.id}`)
    ElMessage.success('已删除')
    fetchSheets()
  } catch { /* cancelled */ }
}

const formatTime = (t) => t ? t.replace('T', ' ').split('.')[0] : ''
const canDelete = (row) => {
  const role = localStorage.getItem('role')
  const userId = parseInt(localStorage.getItem('user_id'))
  return role === 'admin' || row.creator_id === userId
}
onMounted(fetchSheets)
</script>

<style scoped>
.page-container { max-width: 1100px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; }
.page-title { font-size: 1.5rem; font-weight: 700; margin: 0 0 4px; }
.page-subtitle { color: #64748b; font-size: 0.875rem; margin: 0; }
</style>
