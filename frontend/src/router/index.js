import { createRouter, createWebHashHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import ItemCreate from '../views/ItemCreate.vue'
import ItemDetail from '../views/ItemDetail.vue'
import Feedback from '../views/Feedback.vue'
import Todo from '../views/Todo.vue'
import Login from '../views/Login.vue'

import DataStats from '../views/DataStats.vue'
import OperationLog from '../views/OperationLog.vue'

import GroupManagement from '../views/GroupManagement.vue'

const routes = [
    { path: '/login', component: Login },
    { path: '/', component: Dashboard },
    { path: '/item/create', component: ItemCreate },
    { path: '/item/detail/:id', component: ItemDetail },
    { path: '/feedback/:itemId', component: Feedback },
    { path: '/todo', component: Todo },
    { path: '/stats', component: DataStats },
    { path: '/logs', component: OperationLog },
    { path: '/groups', component: GroupManagement },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to, from, next) => {
    const token = localStorage.getItem('token')
    if (to.path !== '/login' && !token) {
        next('/login')
    } else {
        next()
    }
})

export default router
