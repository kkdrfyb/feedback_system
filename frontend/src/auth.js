import { ref, computed } from 'vue'

const token = ref(localStorage.getItem('token'))
const role = ref(localStorage.getItem('role'))
const username = ref(localStorage.getItem('username'))

export const useAuth = () => {
    const isLoggedIn = computed(() => !!token.value)
    const isAdmin = computed(() => role.value === 'admin')

    const setSession = (data) => {
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('role', data.role)
        localStorage.setItem('user_id', data.user_id)
        localStorage.setItem('username', data.name || '管理员')

        token.value = data.access_token
        role.value = data.role
        username.value = data.name || '管理员'
    }

    const clearSession = () => {
        localStorage.clear()
        token.value = null
        role.value = null
        username.value = null
    }

    return {
        token,
        role,
        username,
        isLoggedIn,
        isAdmin,
        setSession,
        clearSession
    }
}
