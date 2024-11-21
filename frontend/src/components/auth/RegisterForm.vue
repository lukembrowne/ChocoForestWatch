<template>
  <div class="register-container">
    <form @submit.prevent="handleRegister">
      <div class="form-group">
        <label>Username:</label>
        <input 
          v-model="username" 
          type="text" 
          required
        />
      </div>
      <div class="form-group">
        <label>Email:</label>
        <input 
          v-model="email" 
          type="email" 
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
      <button type="submit">Register</button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </div>
</template>

<script>
import authService from '../../services/auth';

export default {
  name: 'RegisterForm',
  data() {
    return {
      username: '',
      email: '',
      password: '',
      error: null
    };
  },
  methods: {
    async handleRegister() {
      try {
        await authService.register(this.username, this.email, this.password);
        // After successful registration, log the user in
        await authService.login(this.username, this.password);
        this.$router.push('/projects');
      } catch (error) {
        this.error = error.response?.data?.error || 'Registration failed';
      }
    }
  }
};
</script> 