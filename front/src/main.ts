import './assets/main.css'

import { createApp } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import App from './App.vue'
import Login from "./Login.vue";
import Deposits from "@/Deposits.vue";
import AuthProvider from "@/services/authentication.ts";
import DepositProvider from "@/services/deposit.ts";

const routes = [
  { path: '/', component: Login },
  { path: '/deposit', component: Deposits },
]

const router = createRouter({
  history: createMemoryHistory(),
  routes,
})
const app = createApp(App);

// setup router
app.use(router)
  .mount('#app')

// provider services
app.provide('AuthProvider', AuthProvider)
app.provide('DepositProvider', DepositProvider)
