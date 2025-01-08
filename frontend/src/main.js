import { createApp } from 'vue'
import * as Sentry from "@sentry/vue"
import { Quasar, Dialog } from 'quasar'
import App from './App.vue'
import router from './router'
import './css/app.scss'

// Import Quasar css
import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/dist/quasar.css'

const app = createApp(App)

// Initialize Sentry
Sentry.init({
  app,
  dsn: import.meta.env.VITE_SENTRY_DSN,
  integrations: [
    Sentry.browserTracingIntegration({ router }),
    Sentry.replayIntegration(),
  ],
  
  // Performance Monitoring
  tracesSampleRate: 1.0,
  tracePropagationTargets: ["localhost", /^https:\/\/yourserver\.io\/api/],
  
  // Session Replay
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  environment: import.meta.env.MODE
})

app.use(Quasar, {
  plugins: { Dialog }
})

app.use(router)
app.mount('#app')