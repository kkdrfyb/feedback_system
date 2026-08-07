import axios from 'axios'
const apiBase = `${window.location.protocol}//${window.location.hostname}:8000/api`
console.log("IFMS System - Current API URL:", apiBase)

const apiClient = axios.create({
    baseURL: apiBase,
    timeout: 60000
})
apiClient.interceptors.request.use(config => {
    const token = localStorage.getItem("token")
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
})

// 401 全局拦截：token 过期或无效时清除登录态并跳转登录页
apiClient.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 401) {
            localStorage.clear()
            window.location.hash = '#/login'
        }
        return Promise.reject(error)
    }
)

export default apiClient
