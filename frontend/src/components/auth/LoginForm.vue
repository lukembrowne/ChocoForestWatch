<template>
  <div class="login-container">
    <form @submit.prevent="handleLogin">
      <div class="form-group">
        <label>Username:</label>
        <input 
          v-model="username" 
          type="text" 
          required
        />
      </div>
      <div class="form-group">
        <label>Password:</label>
        <input 
          v-model="password" 
          type="password" 
          required
        />
      </div>
      <button type="submit">Login</button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </div>
</template>

<script>
import authService from '../../services/auth';

export default {
  name: 'LoginForm',
  data() {
    return {
      username: '',
      password: '',
      error: null
    };
  },
  methods: {
    async handleLogin() {
      try {
        await authService.login(this.username, this.password);
        this.$router.push('/projects');
      } catch (error) {
        this.error = error.response?.data?.error || 'Login failed';
      }
    }
  }
};
</script> 