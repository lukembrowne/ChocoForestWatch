import { createI18n } from 'vue-i18n'
import en from '../locales/en.json'
import es from '../locales/es.json'

export default createI18n({
  legacy: false, // Set to false to use Composition API
  locale: 'en', // Default locale
  fallbackLocale: 'en',
  messages: {
    en,
    es
  }
}) 