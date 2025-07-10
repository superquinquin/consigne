import './assets/main.css'

import { createApp } from 'vue'
import { createWebHistory, createRouter } from 'vue-router'

import App from './App.vue'
import ReceiverSelection from './ReceiverSelection.vue'
import Deposits from '@/Deposits.vue'
import AuthProvider from '@/services/authentication.ts'
import DepositProvider from '@/services/deposit.ts'
import UsersProvider from '@/services/users.ts'

const routes = [
  { path: '/', component: ReceiverSelection },
  { path: '/deposit', component: Deposits },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})
const app = createApp(App)

// setup router
app.use(router).mount('#app')

// provider services
app.provide('AuthProvider', AuthProvider)
app.provide('DepositProvider', DepositProvider)
app.provide('UsersProvider', UsersProvider)
