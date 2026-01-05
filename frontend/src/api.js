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
export default apiClient
