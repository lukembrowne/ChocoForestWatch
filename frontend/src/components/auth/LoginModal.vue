<template>
  <q-dialog v-model="dialogOpen" @keydown.escape="closeModal">
    <q-card class="login-modal">
      <q-card-section class="modal-header">
        <div class="header-content">
          <div class="app-title">
            <img src="/favicon/favicon-32x32.png" alt="Choco Forest Watch Logo" class="app-logo" />
            <span class="app-name">Choco Forest Watch</span>
          </div>
          <div class="modal-title">{{ t('auth.modal.title') }}</div>
        </div>
        <q-btn icon="close" flat round dense @click="closeModal" class="close-btn" />
      </q-card-section>

      <q-card-section>
        <q-tabs v-model="activeTab" class="text-primary" align="justify">
          <q-tab name="login" :label="t('auth.modal.tabs.login')" />
          <q-tab name="register" :label="t('auth.modal.tabs.register')" />
        </q-tabs>

        <q-separator />

        <q-tab-panels v-model="activeTab" animated>
          <!-- Login Tab -->
          <q-tab-panel name="login">
            <div class="text-center q-mb-lg">
              <div class="panel-title">{{ t('auth.login.title') }}</div>
            </div>
            
            <q-form @submit.prevent="handleLogin" class="q-gutter-md">
              <!-- Username -->
              <q-input
                v-model="loginForm.username"
                :label="t('auth.login.username')"
                outlined
                :rules="[val => !!val || t('auth.login.usernameRequired')]"
              >
                <template v-slot:prepend>
                  <q-icon name="person" color="primary" />
                </template>
              </q-input>
              
              <!-- Password -->
              <q-input
                v-model="loginForm.password"
                :label="t('auth.login.password')"
                outlined
                :type="showLoginPassword ? 'text' : 'password'"
                :rules="[val => !!val || t('auth.login.passwordRequired')]"
              >
                <template v-slot:prepend>
                  <q-icon name="lock" color="primary" />
                </template>
                <template v-slot:append>
                  <q-icon
                    :name="showLoginPassword ? 'visibility_off' : 'visibility'"
                    class="cursor-pointer"
                    @click="showLoginPassword = !showLoginPassword"
                  />
                </template>
              </q-input>

              <!-- Remember Me & Forgot Password -->
              <div class="row items-center justify-between q-mb-md">
                <q-checkbox 
                  v-model="loginForm.rememberMe" 
                  :label="t('auth.login.rememberMe')"
                  color="primary"
                />
                <q-btn
                  flat
                  dense
                  color="primary"
                  :label="t('auth.login.forgotPassword')"
                  @click="showResetPassword"
                />
              </div>

              <!-- Submit Button -->
              <q-btn
                type="submit"
                color="primary"
                :label="t('auth.login.loginButton')"
                :loading="loginLoading"
                class="full-width q-py-sm"
                size="lg"
              />

              <!-- Create Account Link -->
              <div class="text-center q-mt-md">
                <p class="text-grey-7 q-mb-xs">{{ t('auth.login.noAccount') }}</p>
                <q-btn
                  flat
                  color="primary"
                  :label="t('auth.login.createAccount')"
                  @click="activeTab = 'register'"
                />
              </div>
            </q-form>
          </q-tab-panel>

          <!-- Register Tab -->
          <q-tab-panel name="register">
            <div class="text-center q-mb-lg">
              <div class="panel-title">{{ t('auth.register.title') }}</div>
              <p class="panel-subtitle">{{ t('auth.register.subtitle') }}</p>
            </div>
            
            <q-form @submit.prevent="handleRegister" class="q-gutter-md">
              <!-- Username -->
              <q-input
                v-model="registerForm.username"
                :label="t('auth.login.username')"
                outlined
                :rules="[val => !!val || t('auth.login.usernameRequired')]"
              >
                <template v-slot:prepend>
                  <q-icon name="person" color="primary" />
                </template>
              </q-input>

              <!-- Email -->
              <q-input
                v-model="registerForm.email"
                :label="t('auth.register.email')"
                outlined
                type="email"
                :rules="[
                  val => !!val || t('auth.register.emailRequired'),
                  val => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val) || t('auth.register.invalidEmail')
                ]"
              >
                <template v-slot:prepend>
                  <q-icon name="email" color="primary" />
                </template>
              </q-input>

              <!-- Password -->
              <q-input
                v-model="registerForm.password"
                :label="t('auth.login.password')"
                outlined
                :type="showRegisterPassword ? 'text' : 'password'"
                :rules="[val => !!val || t('auth.login.passwordRequired')]"
              >
                <template v-slot:prepend>
                  <q-icon name="lock" color="primary" />
                </template>
                <template v-slot:append>
                  <q-icon
                    :name="showRegisterPassword ? 'visibility_off' : 'visibility'"
                    class="cursor-pointer"
                    @click="showRegisterPassword = !showRegisterPassword"
                  />
                </template>
              </q-input>

              <!-- Language Preference -->
              <q-select
                v-model="registerForm.preferred_language"
                :options="[
                  { label: 'English', value: 'en' },
                  { label: 'Español', value: 'es' }
                ]"
                :label="t('auth.register.preferredLanguage')"
                outlined
                :rules="[val => !!val || t('auth.login.languageRequired')]"
              >
                <template v-slot:prepend>
                  <q-icon name="language" color="primary" />
                </template>
              </q-select>

              <!-- Submit Button -->
              <q-btn
                type="submit"
                color="primary"
                :label="t('auth.register.createButton')"
                :loading="registerLoading"
                class="full-width q-py-sm"
                size="lg"
              />

              <!-- Login Link -->
              <div class="text-center q-mt-md">
                <p class="text-grey-7 q-mb-xs">{{ t('auth.login.alreadyHaveAccount') }}</p>
                <q-btn
                  flat
                  color="primary"
                  :label="t('auth.login.loginButton')"
                  @click="activeTab = 'login'"
                />
              </div>
            </q-form>
          </q-tab-panel>
        </q-tab-panels>
      </q-card-section>
    </q-card>
  </q-dialog>

  <!-- Reset Password Dialog -->
  <q-dialog v-model="resetPasswordDialog">
    <q-card style="min-width: 350px">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ t('auth.resetPassword.title') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section>
        <p class="text-body2">
          {{ t('auth.resetPassword.instructions') }}
        </p>
        <q-form @submit.prevent="handleResetPassword">
          <q-input
            v-model="resetEmail"
            :label="t('auth.resetPassword.email')"
            type="email"
            outlined
            :rules="[
              val => !!val || t('auth.resetPassword.emailRequired'),
              val => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val) || t('auth.resetPassword.invalidEmail')
            ]"
          >
            <template v-slot:prepend>
              <q-icon name="email" />
            </template>
          </q-input>

          <div class="row justify-end q-mt-md">
            <q-btn :label="t('auth.resetPassword.cancel')" color="primary" flat v-close-popup />
            <q-btn
              :label="t('auth.resetPassword.sendLink')"
              color="primary"
              :loading="resetLoading"
              type="submit"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import authService from '../../services/auth'
import { useAuthStore } from '../../stores/authStore'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  defaultTab: {
    type: String,
    default: 'login',
    validator: (value) => ['login', 'register'].includes(value)
  }
})

const emit = defineEmits(['update:modelValue', 'login-success', 'register-success'])

const $q = useQuasar()
const router = useRouter()
const { t, locale } = useI18n()
const authStore = useAuthStore()

// Modal state
const activeTab = ref(props.defaultTab)
const resetPasswordDialog = ref(false)

// Form data
const loginForm = ref({
  username: '',
  password: '',
  rememberMe: false
})

const registerForm = ref({
  username: '',
  email: '',
  password: '',
  preferred_language: ''
})

const resetEmail = ref('')

// UI state
const showLoginPassword = ref(false)
const showRegisterPassword = ref(false)
const loginLoading = ref(false)
const registerLoading = ref(false)
const resetLoading = ref(false)

// Computed
const dialogOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Methods
const closeModal = () => {
  dialogOpen.value = false
  // Reset forms when modal closes
  loginForm.value = { username: '', password: '', rememberMe: false }
  registerForm.value = { username: '', email: '', password: '', preferred_language: '' }
  resetEmail.value = ''
  activeTab.value = props.defaultTab
}

const handleLogin = async () => {
  try {
    loginLoading.value = true
    const response = await authStore.login(loginForm.value.username, loginForm.value.password)
    
    if (response.user?.preferred_language) {
      locale.value = response.user.preferred_language
      localStorage.setItem('userLanguage', response.user.preferred_language)
    }
    
    $q.notify({
      color: 'positive',
      message: t('auth.login.loginSuccess'),
      icon: 'check'
    })
    
    emit('login-success', response.user)
    closeModal()
    
  } catch (err) {
    const errorMessage = err.response?.data?.error || 'Login failed'
    $q.notify({
      color: 'negative',
      message: errorMessage,
      icon: 'error'
    })
  } finally {
    loginLoading.value = false
  }
}

const handleRegister = async () => {
  try {
    registerLoading.value = true
    await authStore.register(
      registerForm.value.username,
      registerForm.value.email,
      registerForm.value.password,
      registerForm.value.preferred_language.value
    )
    
    // Auto login after registration
    await authStore.login(registerForm.value.username, registerForm.value.password)
    
    $q.notify({
      color: 'positive',
      message: t('auth.register.success'),
      icon: 'check'
    })
    
    emit('register-success', { username: registerForm.value.username })
    closeModal()
    
  } catch (err) {
    let errorMessage = t('auth.register.failed')
    
    if (err.username) {
      errorMessage = err.username[0]
    } else if (err.email) {
      errorMessage = err.email[0]
    } else if (err.details) {
      errorMessage = err.details
    } else if (err.error) {
      errorMessage = err.error
    }

    $q.notify({
      color: 'negative',
      message: errorMessage,
      icon: 'error',
      timeout: 3000,
      position: 'top'
    })
  } finally {
    registerLoading.value = false
  }
}

const showResetPassword = () => {
  resetPasswordDialog.value = true
}

const handleResetPassword = async () => {
  try {
    resetLoading.value = true
    await authService.requestPasswordReset(resetEmail.value)
    
    resetPasswordDialog.value = false
    $q.notify({
      color: 'positive',
      message: t('auth.resetPassword.success'),
      icon: 'check'
    })
    resetEmail.value = ''
  } catch (error) {
    $q.notify({
      color: 'negative',
      message: error.response?.data?.error || t('auth.resetPassword.error'),
      icon: 'error'
    })
  } finally {
    resetLoading.value = false
  }
}

// Watch for prop changes
watch(() => props.defaultTab, (newTab) => {
  activeTab.value = newTab
})
</script>

<style lang="scss" scoped>
.login-modal {
  min-width: 500px;
  max-width: 600px;
  border-radius: 12px;
  overflow: hidden;
}

@media (max-width: 768px) {
  .login-modal {
    min-width: 90vw;
    margin: 1rem;
  }
}

.modal-header {
  background: linear-gradient(135deg, #388e3c 0%, #43a047 100%);
  color: white;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  
  .header-content {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .app-title {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    
    .app-logo {
      width: 28px;
      height: 28px;
      border-radius: 4px;
    }
    
    .app-name {
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.025em;
    }
  }
  
  .modal-title {
    font-size: 1.1rem;
    font-weight: 500;
    opacity: 0.9;
    margin-left: 2rem;
  }
  
  .close-btn {
    color: white;
    opacity: 0.8;
    transition: opacity 0.2s ease;
    
    &:hover {
      opacity: 1;
      background: rgba(255, 255, 255, 0.1);
    }
  }
}

.panel-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.5rem;
  letter-spacing: -0.025em;
}

.panel-subtitle {
  font-size: 1rem;
  color: #64748b;
  margin: 0;
  font-weight: 400;
}

.q-tab-panels {
  margin-top: 1rem;
}

.q-tab-panel {
  padding: 1.5rem 0;
}

:deep(.q-tabs) {
  .q-tab {
    font-weight: 500;
    font-size: 0.95rem;
  }
}

:deep(.q-card) {
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.12), 0 8px 32px rgba(0, 0, 0, 0.08);
}
</style>