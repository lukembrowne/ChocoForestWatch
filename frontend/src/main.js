import { createApp } from 'vue'
import { Quasar, Dialog } from 'quasar'
import App from './App.vue'
import router from './router'

// Import Quasar css
import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/dist/quasar.css'

const app = createApp(App)

app.use(Quasar, {
  plugins: {
    Dialog
  },
  config: {
    // optional if you want to use
    // Quasar's default settings
  }
})

app.use(router)
app.mount('#app')