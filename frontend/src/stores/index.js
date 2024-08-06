import { createPinia } from 'pinia'

export default function (/* { store, ssrContext } */) {
  const pinia = createPinia()

  return pinia
}
