<template>
  <div class="landing-container">
    <!-- Navigation Bar -->
    <div class="nav-bar q-px-lg q-py-md">
      <div class="row justify-between items-center">
        <div class="text-h5 text-weight-bold text-primary">Choco Forest Watch</div>
        <div class="row q-gutter-md">
          <q-btn-group flat>
            <q-btn
              :flat="currentLanguage !== 'English'"
              :color="currentLanguage === 'English' ? 'primary' : 'grey'"
              @click="changeLanguage('en')"
              label="English"
            />
            <q-btn
              :flat="currentLanguage !== 'Español'"
              :color="currentLanguage === 'Español' ? 'primary' : 'grey'"
              @click="changeLanguage('es')"
              label="Español"
            />
          </q-btn-group>
          <q-btn color="primary" :label="t('auth.login.landing.cta.login')" @click="loginDialogOpen = true" />
        </div>
      </div>
    </div>

    <div class="content-wrapper">
      <!-- Hero Section -->
      <div class="hero-section row items-center">
        <div class="col-12 col-md-6 q-pr-md">
          <h1 class="text-h3 text-weight-bold q-mb-md">{{ t('auth.login.landing.tagline') }}</h1>
          <p class="text-h6 q-mb-lg">{{ t('auth.login.landing.subtitle') }}</p>
          <p class="text-body1 q-mb-lg">{{ t('auth.login.landing.motivation') }}</p>
          <div class="row q-gutter-md">
            <q-btn
              color="primary"
              size="lg"
              :label="t('auth.login.landing.cta.createAccount')"
              @click="registerDialogOpen = true"
            />
          </div>
        </div>
        <div class="col-12 col-md-6">
          <q-img src="/images/app-screenshot.jpeg" class="rounded-borders" />
        </div>
      </div>

      <!-- Features and Funding Section -->
      <div class="info-section row q-col-gutter-xl">
        <!-- Features Section -->
        <div class="col-12 col-md-8">
          <h2 class="text-h4 q-mb-lg">{{ t('auth.login.landing.features.title') }}</h2>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-4">
              <q-card class="feature-card">
                <q-card-section class="text-center">
                  <q-icon name="satellite_alt" size="3rem" color="primary" class="q-mb-md" />
                  <div class="text-h6 q-mb-sm">{{ t('auth.login.landing.features.satellite.title') }}</div>
                  <p class="text-body2">{{ t('auth.login.landing.features.satellite.description') }}</p>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-md-4">
              <q-card class="feature-card">
                <q-card-section class="text-center">
                  <q-icon name="psychology" size="3rem" color="primary" class="q-mb-md" />
                  <div class="text-h6 q-mb-sm">{{ t('auth.login.landing.features.ml.title') }}</div>
                  <p class="text-body2">{{ t('auth.login.landing.features.ml.description') }}</p>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-md-4">
              <q-card class="feature-card">
                <q-card-section class="text-center">
                  <q-icon name="monitoring" size="3rem" color="primary" class="q-mb-md" />
                  <div class="text-h6 q-mb-sm">{{ t('auth.login.landing.features.monitoring.title') }}</div>
                  <p class="text-body2">{{ t('auth.login.landing.features.monitoring.description') }}</p>
                </q-card-section>
              </q-card>
            </div>
          </div>
        </div>

        <!-- Funding Section -->
        <div class="col-12 col-md-4">
          <h2 class="text-h4 q-mb-lg">{{ t('auth.login.landing.funding.title') }}</h2>
          <div class="funding-list q-gutter-y-md">
            <div v-for="source in fundingSources" :key="source.name" class="funding-item">
              <q-item>
                <q-item-section avatar>
                  <q-icon :name="source.icon" color="primary" size="sm" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ source.name }}</q-item-label>
                </q-item-section>
              </q-item>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Login Dialog -->
    <q-dialog v-model="loginDialogOpen">
      <q-card class="login-dialog">
        <q-card-section class="text-center">
          <div class="text-h5 text-weight-bold q-mb-sm">{{ t('auth.login.title') }}</div>
          <q-form @submit.prevent="handleLogin" class="q-gutter-md">
            <!-- Username -->
            <div class="input-group">
              <q-input
                v-model="username"
                :label="t('auth.login.username')"
                outlined
                class="full-width"
                :rules="[val => !!val || t('auth.login.usernameRequired')]"
              >
                <template v-slot:prepend>
                  <q-icon name="person" color="primary" />
                </template>
              </q-input>
            </div>
            
            <!-- Password -->
            <div class="input-group">
              <q-input
                v-model="password"
                :label="t('auth.login.password')"
                outlined
                :type="isPwd ? 'password' : 'text'"
                class="full-width"
                :rules="[val => !!val || t('auth.login.passwordRequired')]"
              >
                <template v-slot:prepend>
                  <q-icon name="lock" color="primary" />
                </template>
                <template v-slot:append>
                  <q-icon
                    :name="isPwd ? 'visibility_off' : 'visibility'"
                    class="cursor-pointer"
                    @click="isPwd = !isPwd"
                  />
                </template>
              </q-input>
            </div>

            <!-- Remember Me & Forgot Password -->
            <div class="row items-center justify-between q-mb-md">
              <q-checkbox 
                v-model="rememberMe" 
                :label="t('auth.login.rememberMe')"
                color="primary"
              />
              <q-btn
                flat
                dense
                color="primary"
                :label="t('auth.login.forgotPassword')"
                @click="handleForgotPassword"
              />
            </div>

            <!-- Submit Button -->
            <div class="q-mt-lg">
              <q-btn
                type="submit"
                color="primary"
                :label="t('auth.login.loginButton')"
                :loading="loading"
                class="full-width q-py-sm"
                size="lg"
              />
            </div>

            <!-- Create Account Link -->
            <div class="text-center q-mt-md">
              <p class="text-grey-7 q-mb-xs">{{ t('auth.login.noAccount') }}</p>
              <q-btn
                flat
                color="primary"
                :label="t('auth.login.createAccount')"
                @click="() => { loginDialogOpen = false; registerDialogOpen = true; }"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Register Dialog -->
    <q-dialog v-model="registerDialogOpen">
      <q-card class="register-dialog">
        <q-card-section class="text-center">
          <div class="text-h5 text-weight-bold q-mb-sm">{{ t('auth.register.title') }}</div>
          <p class="text-subtitle1 text-grey-7 q-mb-lg">{{ t('auth.register.subtitle') }}</p>
          
          <q-form @submit.prevent="handleRegister" class="q-gutter-md">
            <!-- Username -->
            <div class="input-group">
              <q-input
                v-model="registerForm.username"
                :label="t('auth.login.username')"
                outlined
                class="full-width"
                :rules="[val => !!val || t('auth.login.usernameRequired')]"
              >
                <template v-slot:prepend>
                  <q-icon name="person" color="primary" />
                </template>
              </q-input>
            </div>

            <!-- Email -->
            <div class="input-group">
              <q-input
                v-model="registerForm.email"
                :label="t('auth.register.email')"
                outlined
                type="email"
                class="full-width"
                :rules="[
                  val => !!val || t('auth.register.emailRequired'),
                  val => /^\w+([.-]?\w+)*@\w+([.-]?\w+)*(\.\w{2,3})+$/.test(val) || t('auth.register.invalidEmail')
                ]"
              >
                <template v-slot:prepend>
                  <q-icon name="email" color="primary" />
                </template>
              </q-input>
            </div>

            <!-- Password -->
            <div class="input-group">
              <q-input
                v-model="registerForm.password"
                :label="t('auth.login.password')"
                outlined
                :type="isRegisterPwd ? 'password' : 'text'"
                class="full-width"
                :rules="[val => !!val || t('auth.login.passwordRequired')]"
              >
                <template v-slot:prepend>
                  <q-icon name="lock" color="primary" />
                </template>
                <template v-slot:append>
                  <q-icon
                    :name="isRegisterPwd ? 'visibility_off' : 'visibility'"
                    class="cursor-pointer"
                    @click="isRegisterPwd = !isRegisterPwd"
                  />
                </template>
              </q-input>
            </div>

            <!-- Language Preference -->
            <div class="input-group">
              <q-select
                v-model="registerForm.preferred_language"
                :options="[
                  { label: 'English', value: 'en' },
                  { label: 'Español', value: 'es' }
                ]"
                :label="t('auth.register.preferredLanguage')"
                outlined
                class="full-width"
              >
                <template v-slot:prepend>
                  <q-icon name="language" color="primary" />
                </template>
              </q-select>
            </div>

            <!-- Submit Button -->
            <div class="q-mt-lg">
              <q-btn
                type="submit"
                color="primary"
                :label="t('auth.register.createButton')"
                :loading="registerLoading"
                class="full-width q-py-sm"
                size="lg"
              />
            </div>

            <!-- Login Link -->
            <div class="text-center q-mt-md">
              <p class="text-grey-7 q-mb-xs">{{ t('auth.login.alreadyHaveAccount') }}</p>
              <q-btn
                flat
                color="primary"
                :label="t('auth.login.loginButton')"
                @click="() => { registerDialogOpen = false; loginDialogOpen = true; }"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Reset Password Dialog -->
    <q-dialog v-model="resetPasswordDialog">
      <!-- Existing reset password dialog content -->
    </q-dialog>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import authService from '../../services/auth'
import axios from 'axios'

export default {
  name: 'LoginForm',
  
  setup() {
    const $q = useQuasar()
    const router = useRouter()
    const { t, locale } = useI18n()
    
    // Initialize locale from localStorage or default to 'en'
    locale.value = localStorage.getItem('userLanguage') || 'en'
    
    const username = ref('')
    const password = ref('')
    const isPwd = ref(true)
    const error = ref(null)
    const loading = ref(false)
    const rememberMe = ref(false)
    const registerDialogOpen = ref(false)
    const isRegisterPwd = ref(true)
    const registerLoading = ref(false)
    const resetPasswordDialog = ref(false)
    const resetEmail = ref('')
    const resetLoading = ref(false)
    const loginDialogOpen = ref(false)
    
    const registerForm = ref({
      username: '',
      email: '',
      password: '',
      preferred_language: locale.value
    })

    const currentLanguage = computed(() => 
      locale.value === 'en' ? 'English' : 'Español'
    )

    const changeLanguage = (lang) => {
      console.log('Changing language to:', lang)
      locale.value = lang
      localStorage.setItem('userLanguage', lang)
    }

    const handleLogin = async () => {
      try {
        loading.value = true
        error.value = null
        const response = await authService.login(username.value, password.value)
        if (response.user?.preferred_language) {
          changeLanguage(response.user.preferred_language)
        }
        router.push('/projects')
        $q.notify({
          color: 'positive',
          message: t('auth.login.loginSuccess'),
          icon: 'check'
        })
      } catch (err) {
        error.value = err.response?.data?.error || 'Login failed'
        $q.notify({
          color: 'negative',
          message: error.value,
          icon: 'error'
        })
      } finally {
        loading.value = false
      }
    }

    const getErrorMessage = (err) => {
      if (typeof err !== 'object') {
        return t('auth.register.failed');
      }

      // Handle specific field errors
      const fieldErrors = {
        username: err.username?.[0],
        email: err.email?.[0],
        password: err.password?.[0]
      };

      // Return the first error message found
      for (const [field, message] of Object.entries(fieldErrors)) {
        if (message) {
          return message;
        }
      }

      // Fallback to generic error message
      return err.error || t('auth.register.failed');
    };

    const handleRegister = async () => {
      try {
        registerLoading.value = true;
        await authService.register(
          registerForm.value.username,
          registerForm.value.email,
          registerForm.value.password,
          registerForm.value.preferred_language
        )
        // Auto login after registration
        await authService.login(registerForm.value.username, registerForm.value.password)
        registerDialogOpen.value = false
        router.push('/projects')
        $q.notify({
          color: 'positive',
          message: t('auth.register.success'),
          icon: 'check'
        });
      } catch (err) {
        let errorMessage = t('auth.register.failed');
        
        // Handle field-specific errors
        if (err.username) {
          errorMessage = err.username[0];
        } else if (err.email) {
          errorMessage = err.email[0];
        } else if (err.details) {
          errorMessage = err.details;
        } else if (err.error) {
          errorMessage = err.error;
        }

        $q.notify({
          color: 'negative',
          message: errorMessage,
          icon: 'error',
          timeout: 3000,
          position: 'top'
        });
      } finally {
        registerLoading.value = false;
      }
    };

    const showRegisterDialog = () => {
      registerDialogOpen.value = true
    }

    const handleForgotPassword = () => {
      resetPasswordDialog.value = true
    }

    const handleResetPassword = async () => {
      try {
        resetLoading.value = true
        await axios.post('http://localhost:8000/api/auth/request-reset/', {
          email: resetEmail.value
        })
        
        resetPasswordDialog.value = false
        $q.notify({
          color: 'positive',
          message: 'Password reset instructions sent to your email',
          icon: 'check'
        })
        resetEmail.value = ''
      } catch (error) {
        $q.notify({
          color: 'negative',
          message: error.response?.data?.error || 'Failed to send reset email',
          icon: 'error'
        })
      } finally {
        resetLoading.value = false
      }
    }

    const fundingSources = [
      {
        name: "Global Forest Watch Small Grants Program",
        icon: "eco"
      },
      {
        name: "Yale Environmental Data Science Initiative",
        icon: "school"
      },
      {
        name: "Tulane Center for AI Excellence",
        icon: "psychology"
      },
      {
        name: "Connolly Alexander Institute",
        icon: "analytics"
      }
    ]

    return {
      username,
      password,
      isPwd,
      error,
      loading,
      rememberMe,
      registerDialogOpen,
      isRegisterPwd,
      registerLoading,
      registerForm,
      currentLanguage,
      changeLanguage,
      handleLogin,
      handleRegister,
      showRegisterDialog,
      handleForgotPassword,
      resetPasswordDialog,
      resetEmail,
      resetLoading,
      handleResetPassword,
      t,
      loginDialogOpen,
      fundingSources
    }
  }
}
</script>

<style lang="scss" scoped>
.landing-container {
  min-height: 100vh;
  background: white;
  overflow: hidden;
}

.content-wrapper {
  height: 100vh;
  padding-top: 64px; // Height of navbar
  display: flex;
  flex-direction: column;
}

.hero-section {
  flex: 1;
  padding: 2rem 4rem;
  background: linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%);
}

.info-section {
  padding: 2rem 4rem;
  background: white;
}

.feature-card {
  height: 100%;
  transition: all 0.3s ease;
  border-radius: 12px;
  overflow: hidden;
  
  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.1);
  }
}

.funding-list {
  .funding-item {
    border-radius: 8px;
    transition: background-color 0.2s;
    
    &:hover {
      background: rgba(0,0,0,0.03);
    }
  }
}

// Responsive adjustments
@media (max-width: 1023px) {
  .content-wrapper {
    height: auto;
  }
  
  .hero-section,
  .info-section {
    padding: 2rem;
  }
}

@media (max-width: 599px) {
  .hero-section,
  .info-section {
    padding: 1rem;
  }
}
</style> 