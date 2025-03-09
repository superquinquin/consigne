import './assets/main.css'

import { createApp } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import App from './App.vue'
import Login from "./Login.vue";
import Deposits from "@/Deposits.vue";

const routes = [
  { path: '/', component: Login },
  { path: '/deposit', component: Deposits },
]

const router = createRouter({
  history: createMemoryHistory(),
  routes,
})
createApp(App)
  .use(router)
  .mount('#app')
