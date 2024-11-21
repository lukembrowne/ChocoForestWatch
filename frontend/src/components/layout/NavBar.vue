<template>
  <nav>
    <div v-if="currentUser">
      <span>Welcome, {{ currentUser.username }}</span>
      <button @click="logout">Logout</button>
    </div>
    <div v-else>
      <router-link to="/login">Login</router-link> |
      <router-link to="/register">Register</router-link>
    </div>
  </nav>
</template>

<script>
import authService from '../../services/auth';

export default {
  name: 'NavBar',
  data() {
    return {
      currentUser: authService.getCurrentUser()
    };
  },
  methods: {
    logout() {
      authService.logout();
      this.$router.push('/login');
    }
  }
};
</script> 