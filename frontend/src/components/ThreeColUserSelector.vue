<template>
  <div class="three-col-selector">
    <!-- Col 1: Groups/Departments -->
    <div class="col-panel group-panel">
      <div class="panel-header">
        <span class="panel-title">组织架构 / 分组</span>
      </div>
      <div class="panel-body">
        <!-- 部门列表 -->
        <div class="group-section-label">部门</div>
        <div 
          v-for="dept in departments" 
          :key="dept" 
          class="list-item" 
          :class="{ active: currentCategory === dept && currentType === 'dept' }"
          @click="selectCategory(dept, 'dept')"
        >
          <el-icon class="icon"><OfficeBuilding /></el-icon>
          <span class="label">{{ dept }}</span>
          <span class="count">{{ getDeptUserCount(dept) }}</span>
        </div>

        <!-- 自定义分组列表 -->
        <div class="group-section-label mt-2" v-if="customGroups.length > 0">我的分组</div>
        <div 
          v-for="g in customGroups" 
          :key="g.id" 
          class="list-item" 
          :class="{ active: currentCategory === g.id && currentType === 'group' }"
          @click="selectCategory(g.id, 'group')"
        >
          <el-icon class="icon"><Collection /></el-icon>
          <span class="label">{{ g.name }}</span>
          <span class="count">{{ g.user_ids.length }}</span>
        </div>
      </div>
    </div>

    <!-- Col 2: Candidates (Users in selected group) -->
    <div class="col-panel member-panel">
      <div class="panel-header">
        <span class="panel-title">{{ currentCategoryName || '请选择分组' }}</span>
        <el-checkbox 
            v-if="currentCategory"
            v-model="isAllCurrentSelected" 
            @change="toggleSelectAllCurrent"
            size="small"
        >全选</el-checkbox>
      </div>
      <div class="panel-body">
        <div v-if="!currentCategory" class="empty-tip">
          <el-icon><Back /></el-icon> 请先在左侧选择分组
        </div>
        <div 
          v-for="user in currentUsers" 
          :key="user.id" 
          class="list-item user-item" 
          :class="{ selected: isSelected(user.id) }"
          @click="toggleUser(user.id)"
        >
          <el-avatar :size="24" class="avatar">{{ user.name.charAt(0) }}</el-avatar>
          <span class="label">{{ user.name }}</span>
          <el-icon v-if="isSelected(user.id)" class="check"><Select /></el-icon>
        </div>
      </div>
    </div>

    <!-- Col 3: Selected Users -->
    <div class="col-panel selected-panel">
      <div class="panel-header">
        <span class="panel-title">已选人员 ({{ modelValue.length }})</span>
        <el-button type="primary" link size="small" @click="clearAll" v-if="modelValue.length > 0">清空</el-button>
      </div>
      <div class="panel-body">
        <div v-if="modelValue.length === 0" class="empty-tip">暂无选择</div>
        <div 
          v-for="user in selectedUserObjects" 
          :key="user.id" 
          class="list-item selected-item"
        >
          <el-avatar :size="24" class="avatar">{{ user.name.charAt(0) }}</el-avatar>
          <div class="info">
             <span class="name">{{ user.name }}</span>
             <span class="dept">{{ user.group }}</span>
          </div>
          <el-icon class="remove-btn" @click="toggleUser(user.id)"><Close /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { OfficeBuilding, Collection, Select, Close, Back } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  allUsers: {
    type: Array,
    required: true
  },
  customGroups: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const currentType = ref('') // 'dept' or 'group'
const currentCategory = ref('') // dept name or group id

// Departments computation
const departments = computed(() => {
  const depts = new Set(props.allUsers.map(u => u.group).filter(Boolean))
  return Array.from(depts)
})

const currentCategoryName = computed(() => {
    if (!currentCategory.value) return ''
    if (currentType.value === 'dept') return currentCategory.value
    const g = props.customGroups.find(g => g.id === currentCategory.value)
    return g ? g.name : ''
})

// Users to show in Middle Column
const currentUsers = computed(() => {
    if (!currentCategory.value) return []
    if (currentType.value === 'dept') {
        return props.allUsers.filter(u => u.group === currentCategory.value)
    } else {
        const g = props.customGroups.find(g => g.id === currentCategory.value)
        if (!g) return []
        return props.allUsers.filter(u => g.user_ids.includes(u.id))
    }
})

// Users object list for Right Column
const selectedUserObjects = computed(() => {
    return props.modelValue.map(id => props.allUsers.find(u => u.id === id)).filter(Boolean)
})

const getDeptUserCount = (dept) => props.allUsers.filter(u => u.group === dept).length

const isSelected = (id) => props.modelValue.includes(id)

const isAllCurrentSelected = computed(() => {
    if (currentUsers.value.length === 0) return false
    return currentUsers.value.every(u => isSelected(u.id))
})

// Actions
function selectCategory(val, type) {
    currentCategory.value = val
    currentType.value = type
}

function toggleUser(id) {
    const newList = [...props.modelValue]
    const idx = newList.indexOf(id)
    if (idx > -1) {
        newList.splice(idx, 1)
    } else {
        newList.push(id)
    }
    emit('update:modelValue', newList)
}

function toggleSelectAllCurrent(val) {
    const currentIds = currentUsers.value.map(u => u.id)
    let newList = [...props.modelValue]
    
    if (val) {
        // Add all not present
        currentIds.forEach(id => {
            if (!newList.includes(id)) newList.push(id)
        })
    } else {
        // Remove all present
        newList = newList.filter(id => !currentIds.includes(id))
    }
    emit('update:modelValue', newList)
}

function clearAll() {
    emit('update:modelValue', [])
}
</script>

<style scoped>
.three-col-selector {
  display: flex;
  height: 450px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: #fff;
}

.col-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color);
  min-width: 0; /* Prevent flex overflow */
}

.col-panel:last-child {
  border-right: none;
}

.panel-header {
  padding: 10px 12px;
  background: #f8fafc;
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--el-text-color-regular);
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.list-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--el-text-color-primary);
  font-size: 0.875rem;
  transition: background 0.2s;
  margin-bottom: 2px;
}

.list-item:hover {
  background: var(--el-fill-color-light);
}

.list-item.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 500;
}

.list-item.selected {
    background: var(--el-color-primary-light-9);
}

.icon { margin-right: 8px; color: var(--el-text-color-secondary); }
.list-item.active .icon { color: var(--el-color-primary); }

.label { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.count { color: var(--el-text-color-secondary); font-size: 12px; }

.group-section-label {
    padding: 8px 10px 4px;
    font-size: 12px;
    color: var(--el-text-color-placeholder);
    font-weight: 700;
}
.mt-2 { margin-top: 8px; }

.empty-tip {
    padding: 20px;
    text-align: center;
    color: var(--el-text-color-placeholder);
    font-size: 13px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
}

/* User Item Specifics */
.user-item .avatar { margin-right: 8px; background: var(--el-color-primary-light-8); color: var(--el-color-primary); font-size: 12px;}
.check { color: var(--el-color-primary); font-weight: bold; }

/* Right Panel Specifics */
.selected-item {
    justify-content: space-between;
    cursor: default;
    background: #fff;
    border: 1px solid transparent;
}
.selected-item:hover {
    border-color: var(--el-border-color-lighter);
}
.info {
    flex: 1;
    display: flex;
    flex-direction: column;
    margin: 0 8px;
    overflow: hidden;
}
.info .name { font-size: 14px; line-height: 1.2; }
.info .dept { font-size: 11px; color: var(--el-text-color-secondary); }
.remove-btn { color: var(--el-text-color-placeholder); cursor: pointer; }
.remove-btn:hover { color: var(--el-color-danger); }

/* Scrollbar refine */
.panel-body::-webkit-scrollbar { width: 4px; }
.panel-body::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 4px; }
</style>
