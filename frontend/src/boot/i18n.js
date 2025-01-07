import { createI18n } from 'vue-i18n'
import messages from '../locales'

const i18n = createI18n({
  legacy: false, // Use Composition API
  locale: localStorage.getItem('locale') || 'en', // Default locale
  fallbackLocale: 'en',
  messages
})

export default ({ app }) => {
  // Install i18n instance on app
  app.use(i18n)
}

export { i18n }