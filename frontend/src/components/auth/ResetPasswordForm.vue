<template>
  <div class="login-container">
    <q-card class="reset-card">
      <q-card-section class="text-center">
        <div class="text-h5">{{ t('auth.resetPassword.title') }}</div>
        <p class="text-subtitle1 text-grey-7">
          {{ t('auth.resetPassword.enterNew') }}
        </p>
      </q-card-section>

      <q-card-section>
        <q-form @submit.prevent="handleResetPassword" class="q-gutter-md">
          <q-input
            v-model="newPassword"
            :label="t('auth.resetPassword.password')"
            outlined
            :type="isPwd ? 'password' : 'text'"
            :rules="[val => !!val || t('auth.login.passwordRequired')]"
            :error="!!error"
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

          <q-input
            v-model="confirmPassword"
            :label="t('auth.resetPassword.confirm')"
            outlined
            :type="isPwd ? 'password' : 'text'"
            :rules="[
              val => !!val || t('auth.resetPassword.confirmRequired'),
              val => val === newPassword || t('auth.resetPassword.mismatch')
            ]"
            :error="!!error"
              :error-message="error"
          >
            <template v-slot:prepend>
              <q-icon name="lock" />
            </template>
          </q-input>

          <q-btn
            type="submit"
            color="primary"
            class="full-width q-mt-lg"
            :loading="loading"
            :label="t('auth.resetPassword.submit')"
          />
        </q-form>
      </q-card-section>
    </q-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import authService from '../../services/auth'

export default {
  name: 'ResetPasswordForm',
  
  setup() {
    const $q = useQuasar()
    const router = useRouter()
    const route = useRoute()
    const { t, locale } = useI18n()
    
    // Initialize locale from localStorage or default to 'en'
    locale.value = localStorage.getItem('userLanguage') || 'en'

    onMounted(() => {
      console.log("Password resset local: ", locale.value)
    })
    
    const newPassword = ref('')
    const confirmPassword = ref('')
    const error = ref(null)
    const loading = ref(false)
    const isPwd = ref(true)

    const handleResetPassword = async () => {
      if (newPassword.value !== confirmPassword.value) {
        error.value = t('auth.resetPassword.mismatch')
        return
      }

      try {
        loading.value = true
        const { uid, token } = route.params
        console.log("Resetting password with uid: ", uid, "and token: ", token)
        await authService.resetPassword(uid, token, newPassword.value)

        $q.notify({
          color: 'positive',
          message: t('auth.resetPassword.resetSuccess'),
          icon: 'check'
        })

        router.push('/login')
      } catch (err) {
        console.log("Error resetting password: ", err)
        error.value = err.response?.data?.error || t('auth.resetPassword.resetFailed')
        $q.notify({
          color: 'negative',
          message: error.value,
          icon: 'error'
        })
      } finally {
        loading.value = false
      }
    }

    return {
      newPassword,
      confirmPassword,
      error,
      loading,
      isPwd,
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

.reset-card {
  width: 400px;
  max-width: 90vw;
  border-radius: 8px;
}
</style> 