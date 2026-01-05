<template>
  <div class="login-container">
    <div class="blob-bg"></div>
    <div class="login-card glass-card">
      <div class="login-header">
        <h2 class="welcome-text">欢迎回来</h2>
        <p class="subtitle-text">事项反馈管理系统 V1.1</p>
      </div>

      <el-form :model="form" class="login-form">
        <el-form-item>
          <el-input 
            v-model="form.username" 
            placeholder="用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-button 
          type="primary" 
          @click="login" 
          class="login-btn"
          size="large"
          loading-icon="Loading"
        >
          即刻登录
        </el-button>
      </el-form>
      
      <div class="login-footer">
        <p>© 2026 Feedback System Pro</p>
      </div>
    </div>
  </div>
</template>

<script>
import apiClient from '../api'
import { useAuth } from '../auth'
import { User, Lock } from '@element-plus/icons-vue'

export default {
  components: { User, Lock },
  setup() {
    return { ...useAuth() }
  },
  data(){ return { form:{username:'',password:''} } },
  methods:{
    async login(){
      try {
        const res = await apiClient.post("/login",{username:this.form.username,password:this.form.password})
        this.setSession(res.data)
        this.$router.push("/")
      } catch (error) {
        console.error("登录失败:", error)
        alert(error.response?.data?.detail || "登录失败，请检查账号密码或后端连接")
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgb(var(--bg-main));
  position: relative;
  overflow: hidden;
}

.blob-bg {
  position: absolute;
  width: 500px;
  height: 500px;
  background: linear-gradient(135deg, rgba(var(--primary), 0.2) 0%, rgba(var(--primary-light), 0.2) 100%);
  filter: blur(80px);
  border-radius: 50%;
  z-index: 0;
  animation: move 20s infinite alternate;
}

@keyframes move {
  from { transform: translate(-10%, -10%); }
  to { transform: translate(10%, 10%); }
}

.login-card {
  width: 400px;
  padding: 3rem 2.5rem;
  z-index: 10;
  text-align: center;
}

.welcome-text {
  font-size: 1.75rem;
  font-weight: 800;
  margin-bottom: 0.5rem;
  color: rgb(var(--text-main));
  letter-spacing: -0.025em;
}

.subtitle-text {
  color: rgb(var(--text-muted));
  margin-bottom: 2.5rem;
  font-size: 0.875rem;
}

.login-form {
  margin-bottom: 2rem;
}

.login-btn {
  width: 100%;
  margin-top: 1rem;
  height: 48px;
  font-size: 1rem;
  letter-spacing: 0.05em;
}

.login-footer {
  font-size: 0.75rem;
  color: rgb(var(--text-muted));
}
</style>
