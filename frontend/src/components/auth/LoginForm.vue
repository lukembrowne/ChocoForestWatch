<template>
  <div class="login-container">
    <q-card class="login-card">
      <q-card-section class="text-center">
        <div class="text-h4 q-mb-md">{{ t('common.login.title') }}</div>
        <div class="text-subtitle1 text-grey-7">
          {{ t('common.login.subtitle') }}
        </div>
        <!-- Simple Language Selector -->
        <div class="row justify-center q-mt-md">
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
        </div>
      </q-card-section>

      <q-card-section>
        <q-form @submit.prevent="handleLogin" class="q-gutter-md">
          <q-input
            v-model="username"
            :label="t('common.login.username')"
            outlined
            :rules="[val => !!val || t('common.login.usernameRequired')]"
            :error="!!error"
          >
            <template v-slot:prepend>
              <q-icon name="person" />
            </template>
          </q-input>

          <q-input
            v-model="password"
            :label="t('common.login.password')"
            outlined
            :type="isPwd ? 'password' : 'text'"
            :rules="[val => !!val || t('common.login.passwordRequired')]"
            :error="!!error"
            :error-message="error"
          >
            <template v-slot:prepend>
              <q-icon name="lock" />
            </template>
            <template v-slot:append>
              <q-icon
                :name="isPwd ? 'visibility_off' : 'visibility'"
                class="cursor-pointer"
                @click="isPwd = !isPwd"
              />
            </template>
          </q-input>

          <div class="row justify-between items-center q-mt-md">
            <q-checkbox v-model="rememberMe" :label="t('common.login.rememberMe')" />
            <q-btn flat color="primary" :label="t('common.login.forgotPassword')" @click="handleForgotPassword" />
          </div>

          <q-btn
            type="submit"
            color="primary"
            class="full-width q-mt-lg"
            size="lg"
            :loading="loading"
            :label="t('common.login.loginButton')"
          />
        </q-form>
      </q-card-section>

      <q-separator />

      <q-card-section class="text-center q-pa-md">
        <p class="text-grey-7 q-mb-sm">{{ t('common.login.noAccount') }}</p>
        <q-btn
          flat
          color="primary"
          :label="t('common.login.createAccount')"
          @click="showRegisterDialog"
        />
      </q-card-section>
    </q-card>

    <!-- Register Dialog -->
    <q-dialog v-model="registerDialogOpen">
      <q-card style="width: 500px; max-width: 90vw;">
        <q-card-section class="text-center">
          <div class="text-h5">Create Account</div>
          <div class="text-subtitle2 text-grey-7">Join Choco Forest Watch</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit.prevent="handleRegister" class="q-gutter-md">
            <q-input
              v-model="registerForm.username"
              label="Username"
              outlined
              :rules="[val => !!val || 'Username is required']"
            >
              <template v-slot:prepend>
                <q-icon name="person" />
              </template>
            </q-input>

            <q-input
              v-model="registerForm.email"
              label="Email"
              outlined
              type="email"
              :rules="[
                val => !!val || 'Email is required',
                val => /.+@.+\..+/.test(val) || 'Invalid email'
              ]"
            >
              <template v-slot:prepend>
                <q-icon name="email" />
              </template>
            </q-input>

            <q-input
              v-model="registerForm.password"
              label="Password"
              outlined
              :type="isRegisterPwd ? 'password' : 'text'"
              :rules="[val => !!val || 'Password is required']"
            >
              <template v-slot:prepend>
                <q-icon name="lock" />
              </template>
              <template v-slot:append>
                <q-icon
                  :name="isRegisterPwd ? 'visibility_off' : 'visibility'"
                  class="cursor-pointer"
                  @click="isRegisterPwd = !isRegisterPwd"
                />
              </template>
            </q-input>

            <q-input
              v-model="registerForm.preferred_language"
              label="Preferred Language"
              outlined
              :options="[
                { label: 'English', value: 'en' },
                { label: 'Español', value: 'es' }
              ]"
              emit-value
              map-options
            >
              <template v-slot:prepend>
                <q-icon name="language" />
              </template>
            </q-input>

            <q-btn
              type="submit"
              color="primary"
              class="full-width q-mt-md"
              :loading="registerLoading"
              label="Create Account"
            />
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Add this dialog -->
    <q-dialog v-model="resetPasswordDialog">
      <q-card style="min-width: 350px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Reset Password</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <p class="text-body2">
            Enter your email address and we'll send you instructions to reset your password.
          </p>
          <q-form @submit.prevent="handleResetPassword">
            <q-input
              v-model="resetEmail"
              label="Email"
              type="email"
              outlined
              :rules="[
                val => !!val || 'Email is required',
                val => /.+@.+\..+/.test(val) || 'Invalid email'
              ]"
            >
              <template v-slot:prepend>
                <q-icon name="email" />
              </template>
            </q-input>

            <div class="row justify-end q-mt-md">
              <q-btn label="Cancel" color="primary" flat v-close-popup />
              <q-btn
                label="Send Reset Link"
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
          message: t('Successfully logged in'),
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

    const handleRegister = async () => {
      try {
        registerLoading.value = true
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
          message: t('Account created successfully!'),
          icon: 'check'
        })
      } catch (err) {
        $q.notify({
          color: 'negative',
          message: err.response?.data?.error || 'Registration failed',
          icon: 'error'
        })
      } finally {
        registerLoading.value = false
      }
    }

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
      t
    }
  }
}
</script>

<style lang="scss" scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #177219 0%, #b1eeb4 100%);
  padding: 20px;
}

.login-card {
  width: 400px;
  max-width: 90vw;
  border-radius: 8px;
}

.q-card {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
</style> 