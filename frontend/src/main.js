import { createApp } from 'vue'
import App from './App.vue'
import { createRouter, createWebHistory } from 'vue-router'
import routes from './router/routes.js'
import { Quasar } from 'quasar'
import quasarUserOptions from './quasar-user-options'
import 'quasar/src/css/index.sass'

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)
app.use(router)
app.use(Quasar, quasarUserOptions)
app.mount('#app')