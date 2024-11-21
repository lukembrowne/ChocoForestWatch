<template>
  <div class="login-container">
    <q-card class="reset-card">
      <q-card-section class="text-center">
        <div class="text-h5">Reset Password</div>
        <p class="text-subtitle1 text-grey-7">
          Enter your new password
        </p>
      </q-card-section>

      <q-card-section>
        <q-form @submit.prevent="handleResetPassword" class="q-gutter-md">
          <q-input
            v-model="newPassword"
            label="New Password"
            outlined
            :type="isPwd ? 'password' : 'text'"
            :rules="[val => !!val || 'Password is required']"
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
            label="Confirm Password"
            outlined
            :type="isPwd ? 'password' : 'text'"
            :rules="[
              val => !!val || 'Password confirmation is required',
              val => val === newPassword || 'Passwords do not match'
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
            label="Reset Password"
          />
        </q-form>
      </q-card-section>
    </q-card>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import axios from 'axios'

export default {
  name: 'ResetPasswordForm',
  
  setup() {
    const $q = useQuasar()
    const router = useRouter()
    const route = useRoute()
    
    const newPassword = ref('')
    const confirmPassword = ref('')
    const error = ref(null)
    const loading = ref(false)
    const isPwd = ref(true)

    const handleResetPassword = async () => {
      if (newPassword.value !== confirmPassword.value) {
        error.value = 'Passwords do not match'
        return
      }

      try {
        loading.value = true
        const { uid, token } = route.params
        
        await axios.post(`http://localhost:8000/api/auth/reset-password/${uid}/${token}/`, {
          new_password: newPassword.value
        })

        $q.notify({
          color: 'positive',
          message: 'Password reset successful! Please login with your new password.',
          icon: 'check'
        })

        router.push('/login')
      } catch (err) {
        error.value = err.response?.data?.error || 'Failed to reset password'
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
      handleResetPassword
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