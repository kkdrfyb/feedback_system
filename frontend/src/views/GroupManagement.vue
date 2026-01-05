<template>
  <div class="page-container">
    <div class="sidebar">
      <div class="sidebar-header">
        <el-input v-model="searchQuery" placeholder="搜索分组..." :prefix-icon="Search" class="search-input" />
        <div class="action-buttons">
          <el-button type="primary" @click="openDialog()" class="create-btn">
            <el-icon><Plus /></el-icon> 创建新分组
          </el-button>
          <el-button class="secondary-btn" @click="importDialogVisible = true">
            <el-icon><Upload /></el-icon> 批量导入
          </el-button>
          <el-button class="secondary-btn" @click="userMgmtVisible = true">
            <el-icon><User /></el-icon> 用户管理
          </el-button>
        </div>
      </div>

      <div class="groups-list">
        <!-- Standard Groups -->
        <div class="group-category">
          <h3>默认分组</h3>
          <div class="group-cards">
            <div v-for="group in orgGroups" :key="group.id" 
                 class="group-card"
                 :class="{ active: currentGroup?.id === group.id }"
                 @click="selectGroup(group)">
              <div class="group-info">
                <span class="group-name">{{ group.name }}</span>
                <span class="member-count">{{ group.user_ids.length }} 人</span>
              </div>
              <el-icon class="arrow-icon"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>

        <!-- Custom Groups -->
        <div class="group-category">
          <h3>自定义分组</h3>
          <el-empty v-if="customGroups.length === 0" description="暂无自定义分组" :image-size="60" />
          <div class="group-cards" v-else>
            <div v-for="group in customGroups" :key="group.id" 
                 class="group-card"
                 :class="{ active: currentGroup?.id === group.id }"
                 @click="selectGroup(group)">
              <div class="group-info">
                <span class="group-name">{{ group.name }}</span>
                <span class="member-count">{{ group.user_ids.length }} 人</span>
              </div>
              <div class="card-actions">
                <el-button link type="primary" @click.stop="openDialog(group)">编辑</el-button>
                <el-button link type="danger" @click.stop="deleteGroup(group.id)">删除</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Panel: Group Details -->
    <div class="group-detail-panel" v-if="currentGroup">
      <div class="detail-header">
        <div>
          <h2>{{ currentGroup.name }} ({{ currentGroup.user_ids.length }}人)</h2>
          <p class="group-desc">{{ currentGroup.description || '暂无描述' }}</p>
        </div>
        <el-button type="primary" v-if="!currentGroup.is_org" @click="openDialog(currentGroup)">编辑分组</el-button>
      </div>
      
      <div class="members-grid">
        <div v-for="user in currentGroupUsers" :key="user.id" class="member-card">
          <div class="avatar-placeholder">{{ user.name.charAt(0) }}</div>
          <div class="member-info">
            <span class="member-name">{{ user.name }}</span>
            <span class="member-role">{{ user.role === 'admin' ? '管理员' : '反馈人员' }}</span>
          </div>
        </div>
        <el-empty v-if="currentGroupUsers.length === 0" description="该分组暂无成员" />
      </div>
    </div>
    
    <div class="empty-state" v-else>
      <el-empty description="请选择左侧分组查看详情" />
    </div>

    <!-- Create/Edit Group Dialog -->
    <el-dialog 
        v-model="dialogVisible" 
        :title="editingGroup ? '编辑分组' : '创建新分组'" 
        width="600px"
        append-to-body
        destroy-on-close
        class="custom-dialog">
        
        <el-form label-position="top">
            <el-form-item label="分组名称">
                <el-input v-model="form.name" placeholder="例如：技术部-后端组" />
            </el-form-item>
            
            <el-form-item label="分组描述">
                <el-input v-model="form.description" type="textarea" />
            </el-form-item>
            <el-form-item label="类型" v-if="isAdmin">
                <el-radio-group v-model="form.is_org">
                    <el-radio :label="false">个人私有</el-radio>
                    <el-radio :label="true">全院公开 (组织机构)</el-radio>
                </el-radio-group>
            </el-form-item>
            <el-form-item label="选择成员 (右侧添加)" required>
                <ThreeColUserSelector 
                    :all-users="allUsers" 
                    v-model="form.user_ids" 
                    class="user-selector"
                />
            </el-form-item>
        </el-form>
        
        <template #footer>
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" @click="saveGroup">保存</el-button>
        </template>
    </el-dialog>

    <!-- Import Dialog -->
    <el-dialog
        v-model="importDialogVisible"
        title="批量导入分组人员"
        width="500px"
        append-to-body>
        <div class="upload-area">
            <p>请上传 CSV 文件，格式：name, username, password, role, group</p>
            <input type="file" @change="handleFileUpload" accept=".csv" />
        </div>
        <template #footer>
            <el-button @click="importDialogVisible = false">关闭</el-button>
            <el-button type="primary" @click="uploadCSV">上传</el-button>
        </template>
    </el-dialog>

    <!-- User Management Dialog -->
    <el-dialog
        v-model="userMgmtVisible"
        title="系统用户管理"
        width="800px"
        append-to-body>
        
        <div class="user-mgmt-toolbar">
            <el-button type="primary" @click="showAddUser = true">
                <el-icon><Plus /></el-icon> 新增用户
            </el-button>
            <el-button type="success" @click="exportUsers">
                <el-icon><Download /></el-icon> 导出用户列表
            </el-button>
        </div>

        <!-- Add User Inline Form -->
        <div v-if="showAddUser" class="add-user-form">
            <h4>新增用户</h4>
            <el-form :inline="true" :model="newUserForm" class="demo-form-inline">
                <el-form-item label="姓名">
                    <el-input v-model="newUserForm.name" placeholder="姓名" />
                </el-form-item>
                <el-form-item label="用户名">
                    <el-input v-model="newUserForm.username" placeholder="登录账号" />
                </el-form-item>
                <el-form-item label="密码">
                    <el-input v-model="newUserForm.password" placeholder="默认密码" />
                </el-form-item>
                <el-form-item label="角色">
                     <el-select v-model="newUserForm.role" placeholder="角色" style="width: 100px">
                        <el-option label="普通用户" value="feedbacker" />
                        <el-option label="管理员" value="admin" />
                    </el-select>
                </el-form-item>
                <el-form-item label="部门">
                     <el-select v-model="newUserForm.group" placeholder="部门/组" style="width: 140px">
                        <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
                     </el-select>
                </el-form-item>
                 <el-form-item>
                    <el-button type="primary" @click="addUser">确认添加</el-button>
                    <el-button @click="showAddUser = false">取消</el-button>
                </el-form-item>
            </el-form>
        </div>

        <el-table :data="allUsers" height="400" style="width: 100%; margin-top: 1rem;">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="姓名" width="120" />
            <el-table-column prop="username" label="用户名" width="120" />
            <el-table-column prop="role" label="角色" width="100">
                <template #default="scope">
                    <el-tag :type="scope.row.role === 'admin' ? 'danger' : ''">{{ scope.row.role }}</el-tag>
                </template>
            </el-table-column>
            <el-table-column prop="group" label="部门/组" />
            <el-table-column label="默认密码提示" width="120">
                <template #default="scope">
                    <span>123</span>
                </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
                <template #default="scope">
                    <el-button link type="danger" size="small" @click="deleteUser(scope.row)">删除</el-button>
                </template>
            </el-table-column>
        </el-table>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import apiClient from '../api'
import { Plus, Upload, Search, ArrowRight, User, Download } from '@element-plus/icons-vue'
import ThreeColUserSelector from '../components/ThreeColUserSelector.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const userId = parseInt(localStorage.getItem('user_id'))
const role = localStorage.getItem('role')
const isAdmin = computed(() => role === 'admin') // Added back isAdmin logic

const groups = ref([])
const allUsers = ref([])
const currentGroup = ref(null)
const searchQuery = ref('')
const dialogVisible = ref(false)
const editingGroup = ref(null)
const importDialogVisible = ref(false)
const selectedFile = ref(null)

// User Management Refs
const userMgmtVisible = ref(false)
const showAddUser = ref(false)
const newUserForm = ref({
    name: '',
    username: '',
    password: '',
    role: 'feedbacker',
    group: '默认组'
})

const form = ref({
    name: '',
    description: '',
    is_org: false,
    user_ids: []
})

const orgGroups = computed(() => groups.value.filter(g => g.is_org))
const customGroups = computed(() => groups.value.filter(g => !g.is_org && g.name.includes(searchQuery.value)))
const departments = computed(() => Array.from(new Set(allUsers.value.map(u => u.group).filter(Boolean))))

// Users in the correctly selected group
const currentGroupUsers = computed(() => {
    if (!currentGroup.value) return []
    return allUsers.value.filter(u => currentGroup.value.user_ids.includes(u.id))
})

onMounted(async () => {
    try {
        console.log('GroupManagement mounted, fetching data...')
        try { await apiClient.post('/groups/sync_org') } catch(e) {}
        fetchGroups()
        loadUsers()
    } catch (e) {
        console.error("Failed to load group data", e)
        ElMessage.error("数据加载失败: " + e.message)
    }
})

async function loadUsers() {
    const uRes = await apiClient.get('/users')
    allUsers.value = uRes.data
    console.log('Users loaded:', allUsers.value.length)
}

async function fetchGroups() {
    try {
        const res = await apiClient.get('/groups', { params: { user_id: userId, role: role } })
        groups.value = res.data
        console.log('Groups loaded:', groups.value.length)
        if (!currentGroup.value && groups.value.length > 0) {
            currentGroup.value = groups.value[0]
        }
    } catch (e) {
        console.error("Failed to fetch groups", e)
    }
}

function selectGroup(group) {
    currentGroup.value = group
}

function openDialog(group = null) {
    if (group) {
        editingGroup.value = group
        form.value = {
            name: group.name,
            description: group.description,
            is_org: group.is_org,
            user_ids: [...group.user_ids]
        }
    } else {
        editingGroup.value = null
        form.value = { name: '', description: '', is_org: false, user_ids: [] }
    }
    dialogVisible.value = true
}

async function saveGroup() {
    try {
        if (editingGroup.value) {
            await apiClient.put(`/groups/${editingGroup.value.id}`, form.value, { params: { user_id: userId, role } })
            ElMessage.success('更新成功')
        } else {
            await apiClient.post('/groups', form.value, { params: { owner_id: userId, role } })
            ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchGroups()
    } catch (err) {
        ElMessage.error('保存失败')
    }
}

async function deleteGroup(id) {
    try {
        await ElMessageBox.confirm('确认删除该分组?', '提示', { type: 'warning' })
        await apiClient.delete(`/groups/${id}`, { params: { user_id: userId, role } })
        ElMessage.success('删除成功')
        currentGroup.value = null
        fetchGroups()
    } catch (e) {
        // Cancelled
    }
}

function handleFileUpload(event) {
    selectedFile.value = event.target.files[0]
}

async function uploadCSV() {
    if (!selectedFile.value) return alert("请选择文件")
    const formData = new FormData()
    formData.append("file", selectedFile.value)
    try {
        await apiClient.post("/groups/import", formData, { params: { owner_id: userId } })
        ElMessage.success("导入成功")
        importDialogVisible.value = false
        fetchGroups()
        loadUsers()
    } catch (e) {
        ElMessage.error("导入失败: " + e.message)
    }
}

// User Management Functions
async function addUser() {
    if (!newUserForm.value.username || !newUserForm.value.password) {
        return ElMessage.warning("请填写完整信息")
    }
    try {
        await apiClient.post('/users', newUserForm.value)
        ElMessage.success("用户添加成功")
        loadUsers()
        newUserForm.value = { name: '', username: '', password: '', role: 'feedbacker', group: '默认组' }
        showAddUser.value = false
    } catch (e) {
        ElMessage.error("添加失败: " + (e.response?.data?.detail || e.message))
    }
}

async function deleteUser(user) {
    try {
        await ElMessageBox.confirm(`确认删除用户 ${user.name}?`, '警告', { type: 'warning' })
        await apiClient.delete(`/users/${user.id}`)
        ElMessage.success("删除成功")
        loadUsers()
    } catch (e) {
        // Cancel
    }
}

function exportUsers() {
    apiClient.get('/users/export', { responseType: 'blob' }).then(res => {
        const url = window.URL.createObjectURL(new Blob([res.data]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', 'users_export.csv')
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }).catch(e => {
        ElMessage.error("导出失败")
    })
}
</script>

<style scoped>
.page-container {
    height: calc(100vh - 84px); /* Adjust based on navbar height */
    display: flex;
    background: #fff;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
    margin: -24px; /* Fill parent */
}

/* Left Sidebar */
.sidebar {
    width: 320px;
    background: #f8fafc;
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
}

.sidebar-header {
    padding: 1.5rem;
    border-bottom: 1px solid var(--border-color);
    background: #fff;
}

.search-input {
    margin-bottom: 1rem;
}

.action-buttons {
    display: flex;
    flex-wrap: wrap; /* allow wrap if too small */
    gap: 0.5rem;
}

.create-btn {
    flex: 1;
}

.secondary-btn {
    padding: 8px 12px;
}

.groups-list {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
}

.group-category h3 {
    font-size: 0.75rem;
    text-transform: uppercase;
    color: #64748b;
    margin: 1rem 0 0.5rem 0.5rem;
    font-weight: 600;
}

.group-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: #fff;
    border-radius: 8px;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid transparent;
}

.group-card:hover {
    background: #f1f5f9;
}

.group-card.active {
    background: #eef2ff;
    border-color: #c7d2fe;
}

.group-info {
    display: flex;
    flex-direction: column;
}

.group-name {
    font-weight: 500;
    color: #1e293b;
}

.member-count {
    font-size: 0.75rem;
    color: #64748b;
}

.arrow-icon {
    color: #94a3b8;
}

.card-actions {
    display: none;
}

.group-card:hover .card-actions {
    display: flex;
}

/* Right Detail Panel */
.group-detail-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 2rem;
    overflow-y: auto;
}

.detail-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
}

.detail-header h2 {
    margin: 0 0 0.5rem 0;
    color: #1e293b;
}

.group-desc {
    color: #64748b;
    margin: 0;
}

.members-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1.5rem;
}

.member-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: #fff;
}

.avatar-placeholder {
    width: 40px;
    height: 40px;
    background: #eef2ff;
    color: var(--primary);
    border-radius: 99px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
}

.member-info {
    display: flex;
    flex-direction: column;
}

.member-name {
    font-weight: 500;
    color: #1e293b;
}

.member-role {
    font-size: 0.75rem;
    color: #64748b;
}

.empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
}

.upload-area {
    padding: 2rem;
    text-align: center;
    border: 2px dashed var(--border-color);
    border-radius: 8px;
    color: #64748b;
}

/* User Management Styles */
.user-mgmt-toolbar {
    display: flex;
    justify-content: space-between;
    margin-bottom: 1.5rem;
}

.add-user-form {
    background: #f8fafc;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    border: 1px solid var(--border-color);
}

.add-user-form h4 {
    margin: 0 0 1rem 0;
    font-size: 0.875rem;
    color: #64748b;
}
</style>
