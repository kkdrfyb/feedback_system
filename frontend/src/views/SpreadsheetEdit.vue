<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header">
      <div>
        <el-button link @click="$router.push('/spreadsheets')" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 表格列表
        </el-button>
        <h1 class="page-title">{{ sheet?.title || '加载中…' }}</h1>
        <p class="page-subtitle" v-if="sheet">
          {{ sheet.rows?.length || 0 }} 行 × {{ sheet.columns?.length || 0 }} 列 ·
          点击单元格即可编辑，失去焦点自动保存
        </p>
      </div>
      <el-button type="success" @click="doExport" :loading="exporting">
        <el-icon><Download /></el-icon> 导出 Excel
      </el-button>
    </div>

    <div class="table-wrapper" v-if="sheet">
      <div class="table-scroll">
        <table class="spreadsheet-table">
          <thead>
            <tr>
              <th class="row-num">#</th>
              <th v-for="col in sheet.columns" :key="col.key" :style="{ minWidth: (col.width || 150) + 'px' }">
                {{ col.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in sheet.rows" :key="row.id">
              <td class="row-num">{{ ri + 1 }}</td>
              <td
                v-for="col in sheet.columns"
                :key="col.key"
                :class="{ editing: isEditing(row.id, col.key) }"
                @click="startEdit(row.id, col.key, row.data?.[col.key] || '')"
              >
                <template v-if="isEditing(row.id, col.key)">
                  <input
                    ref="editInput"
                    v-model="editValue"
                    class="cell-input"
                    @blur="saveEdit(row.id, col.key)"
                    @keydown.enter="saveEdit(row.id, col.key)"
                    @keydown.escape="cancelEdit"
                  />
                </template>
                <template v-else>
                  <span class="cell-text">{{ row.data?.[col.key] || '' }}</span>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="table-footer" v-if="sheet">
        <span>最后更新：{{ formatTime(sheet.updated_at || sheet.created_at) }}</span>
        <span v-if="lastSaved" class="save-indicator">{{ lastSaved }}</span>
      </div>
    </div>

    <el-empty v-if="!loading && !sheet" description="表格不存在或已删除" />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import apiClient from '../api'
import { ArrowLeft, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const route = useRoute()
const sheet = ref(null)
const loading = ref(false)
const exporting = ref(false)
const lastSaved = ref('')

// 编辑状态
const editingRowId = ref(null)
const editingColKey = ref(null)
const editValue = ref('')
const saving = ref(false)

const isEditing = (rowId, key) => editingRowId.value === rowId && editingColKey.value === key

const startEdit = (rowId, key, currentVal) => {
  if (saving.value) return
  editingRowId.value = rowId
  editingColKey.value = key
  editValue.value = currentVal
  nextTick(() => {
    const inputs = document.querySelectorAll('.cell-input')
    if (inputs.length) inputs[inputs.length - 1].focus()
  })
}

const cancelEdit = () => {
  editingRowId.value = null
  editingColKey.value = null
  editValue.value = ''
}

const saveEdit = async (rowId, key) => {
  if (saving.value) return
  saving.value = true
  const val = editValue.value
  cancelEdit()
  try {
    await apiClient.put(`/spreadsheets/${sheet.value.id}/cells`, { row_id: rowId, key, value: val })
    // 更新本地数据
    const row = sheet.value.rows.find(r => r.id === rowId)
    if (row) {
      if (!row.data) row.data = {}
      row.data[key] = val
    }
    lastSaved.value = '已保存 ' + new Date().toLocaleTimeString()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

const fetchSheet = async () => {
  loading.value = true
  try {
    const id = route.params.id
    const res = await apiClient.get(`/spreadsheets/${id}`)
    sheet.value = res.data
  } catch (e) {
    ElMessage.error('加载表格失败')
  } finally {
    loading.value = false
  }
}

const doExport = async () => {
  exporting.value = true
  try {
    const res = await apiClient.get(`/spreadsheets/${sheet.value.id}/export`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url; a.download = `${sheet.value.title}_export.xlsx`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch { ElMessage.error('导出失败') } finally { exporting.value = false }
}

const formatTime = (t) => t ? t.replace('T', ' ').split('.')[0] : ''
onMounted(fetchSheet)
</script>

<style scoped>
.page-container { max-width: 100%; margin: 0 auto; padding: 0 24px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 1.5rem; font-weight: 700; margin: 4px 0 4px; }
.page-subtitle { color: #64748b; font-size: 0.875rem; margin: 0; }
.back-btn { color: #64748b; padding: 0; }

.table-wrapper { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; background: #fff; }
.table-scroll { overflow-x: auto; }
.spreadsheet-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.spreadsheet-table th {
  background: #f8fafc; color: #475569; font-weight: 600; padding: 10px 12px;
  border-bottom: 2px solid #e5e7eb; text-align: left; white-space: nowrap;
  position: sticky; top: 0; z-index: 2;
}
.spreadsheet-table td {
  padding: 6px 12px; border-bottom: 1px solid #f1f5f9; min-height: 36px;
  cursor: pointer; transition: background 0.15s;
}
.spreadsheet-table td:hover { background: #f8fafc; }
.spreadsheet-table td.editing { padding: 2px 4px; background: #eff6ff; }
.row-num { width: 48px; text-align: center; color: #94a3b8; font-size: 0.8rem; cursor: default !important; }
.cell-text { display: block; min-height: 22px; line-height: 22px; }
.cell-input {
  width: 100%; border: 1px solid #3b82f6; border-radius: 3px; padding: 4px 6px;
  font-size: 0.875rem; outline: none; box-sizing: border-box; font-family: inherit;
}
.table-footer { padding: 10px 16px; background: #f8fafc; color: #94a3b8; font-size: 0.8rem; display: flex; justify-content: space-between; }
.save-indicator { color: #22c55e; font-weight: 500; }
</style>
