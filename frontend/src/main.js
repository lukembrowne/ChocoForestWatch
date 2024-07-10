import { createApp } from 'vue'
import { Quasar } from 'quasar'
import quasarUserOptions from './quasar-user-options'
import App from './App.vue'
import router from './router'
import createStore from './stores'

const app = createApp(App)

app.use(Quasar, quasarUserOptions)
app.use(router)
app.use(createStore())

app.mount('#app')