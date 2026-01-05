<template>
  <el-table :data="items">
    <el-table-column prop="title" label="标题" />
    <el-table-column prop="status" label="状态" />
    <el-table-column prop="deadline" label="截止时间" />
    <el-table-column label="操作">
      <template #default="scope">
        <el-button size="mini" @click="$router.push('/item/detail/'+scope.row.id)">详情</el-button>
        <el-button size="mini" type="success" v-if="scope.row.status=='pending'" @click="$router.push('/feedback/'+scope.row.id)">反馈</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script>
export default {
  props: { items:Array }
}
</script>
