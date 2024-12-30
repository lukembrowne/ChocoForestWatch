import { createI18n } from 'vue-i18n'
import en from 'src/i18n/en.js'
import es from 'src/i18n/es.js'

const messages = {
    en,
    es
}

export default ({ app }) => {
  // Create I18n instance
  const i18n = createI18n({
    locale: 'en',
    legacy: false, // comment this out if not using Composition API
    messages
  })

  // Tell app to use the I18n instance
  app.use(i18n)
}