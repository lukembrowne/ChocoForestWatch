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

    <!-- Main Content Section -->
    <div class="content-wrapper">
      <!-- Hero Section with Integrated Features -->
      <div class="hero-section">
        <div class="row items-center justify-between q-pl-xl q-pr-xl">
          <!-- Left Column: Hero Content -->
          <div class="col-12 col-md-6 hero-content q-pr-md">
            <h1 class="text-h3 text-weight-bold q-mb-md">{{ t('auth.login.landing.tagline') }}</h1>
            <p class="text-h6 q-mb-lg">{{ t('auth.login.landing.subtitle') }}</p>
            <p class="text-body1 q-mb-lg">{{ t('auth.login.landing.motivation') }}</p>
            <div class="row q-gutter-md q-mb-xl justify-center">
              <q-btn
                color="primary"
                size="lg"
                :label="t('auth.login.landing.cta.createAccount')"
                @click="registerDialogOpen = true"
              />
            </div>

            <!-- Feature Cards -->
            <div class="row q-col-gutter-md features-grid">
              <div class="col-12 col-sm-4" v-for="(feature, index) in features" :key="index">
                <q-card flat bordered class="feature-card">
                  <q-card-section class="text-center">
                    <q-icon :name="feature.icon" size="2.5rem" color="primary" class="q-mb-sm" />
                    <div class="text-subtitle1 text-weight-bold q-mb-xs">{{ t(feature.title) }}</div>
                    <p class="text-caption">{{ t(feature.description) }}</p>
                  </q-card-section>
                </q-card>
              </div>
            </div>
          </div>

          <!-- Right Column: Image -->
          <div class="col-12 col-md-6 hero-image">
            <q-img 
              src="/images/SCR-20250124-iyyd.png" 
              class="rounded-borders"
              style="box-shadow: 0 8px 30px rgba(0,0,0,0.12);"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <footer class="footer-section q-px-sm">
      <div class="row">
        <div class="col-12">
          <h5 class="text-h6 text-weight-bold q-mb-md">{{ t('auth.login.landing.funding.title') }}</h5>
          <div class="row q-col-gutter-md">
            <div v-for="source in fundingSources" :key="source.name" class="col-12 col-sm-6 col-md-3">
              <div class="funding-item">
                <q-item dense class="q-pa-md">
                  <q-item-section avatar>
                    <q-icon :name="source.icon" color="primary" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ source.name }}</q-item-label>
                  </q-item-section>
                </q-item>
              </div>
            </div>
          </div>
          <div class="text-center q-mt-lg text-caption text-grey">
          </div>
        </div>
      </div>
    </footer>

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
                :rules="[val => !!val || t('auth.login.languageRequired')]"
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
      <q-card class="modern-menu" style="min-width: 350px">
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
                val => /.+@.+\..+/.test(val) || t('auth.resetPassword.invalidEmail')
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
      preferred_language: ''
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
          registerForm.value.preferred_language.value // Need to pass two leter code
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

    const fundingSources = [
      {
        name: "Global Forest Watch Small Grants Program and the World Resources Institute",
        icon: "eco"
      },
      {
        name: "Yale Environmental Data Science Initiative (YEDSI)",
        icon: "school"
      },
      {
        name: "Tulane Center of Excellence for Community-Engaged Artificial Intelligence (CEAI)",
        icon: "psychology"
      },
      {
        name: "The Connolly Alexander Institute for Data Science (CAIDS)",
        icon: "analytics"
      }
    ]

    const features = [
      {
        icon: 'satellite_alt',
        title: 'auth.login.landing.features.satellite.title',
        description: 'auth.login.landing.features.satellite.description'
      },
      {
        icon: 'psychology',
        title: 'auth.login.landing.features.ml.title',
        description: 'auth.login.landing.features.ml.description'
      },
      {
        icon: 'monitoring',
        title: 'auth.login.landing.features.monitoring.title',
        description: 'auth.login.landing.features.monitoring.description'
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
      fundingSources,
      features
    }
  }
}
</script>

<style lang="scss" scoped>
.landing-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: white;
}

.content-wrapper {
  flex: 1;
}

.hero-section {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  min-height: calc(100vh - 64px - 200px); // Viewport height minus header and footer
  display: flex;
  align-items: center;
}

.hero-content {
  .feature-card {
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(0,0,0,0.1);
    transition: all 0.3s ease;

    &:hover {
      transform: translateY(-5px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.1);
    }
  }
}

.hero-image {
  display: flex;
  align-items: center;
  justify-content: center;
}

.footer-section {
  background: #f8f9fa;
  border-top: 1px solid rgba(0,0,0,0.1);
  margin-top: auto;

  .funding-item {
    background: white;
    border-radius: 8px;
    transition: all 0.2s ease;
    height: 100%;

    &:hover {
      background: #f1f1f1;
      transform: translateY(-2px);
    }

    .q-item {
      min-height: unset;
    }

    .q-item-label {
      font-size: 0.875rem;
      line-height: 1.4;
    }
  }
}

.register-dialog {
  min-width: 500px;
}

@media (max-width: 1023px) {
  .hero-section {
    min-height: auto;
    padding: 2rem 0;
  }

  .hero-content {
    order: 1;
  }

  .hero-image {
    order: 0;
    margin-bottom: 2rem;
  }
}

@media (max-width: 599px) {
  .features-grid {
    margin-top: 2rem;
  }
}
</style> 