export default {
  common: {
    loading: 'Loading...',
    error: 'An error occurred',
    save: 'Save',
    cancel: 'Cancel',
    logout: 'Logout',
    login: {
      title: 'Choco Forest Watch',
      subtitle: 'Monitor and analyze forest cover changes using satellite imagery and machine learning',
      username: 'Username',
      password: 'Password',
      rememberMe: 'Remember me',
      forgotPassword: 'Forgot password?',
      loginButton: 'Login',
      noAccount: 'Don\'t have an account?',
      createAccount: 'Create Account',
      usernameRequired: 'Username is required',
      passwordRequired: 'Password is required',
      loginSuccess: 'Successfully logged in',
      loginFailed: 'Login failed'
    },
    register: {
      title: 'Create Account',
      subtitle: 'Join Choco Forest Watch',
      email: 'Email',
      emailRequired: 'Email is required',
      invalidEmail: 'Invalid email',
      preferredLanguage: 'Preferred Language',
      createButton: 'Create Account',
      success: 'Account created successfully!',
      failed: 'Registration failed'
    },
    resetPassword: {
      title: 'Reset Password',
      instructions: 'Enter your email address and we\'ll send you instructions to reset your password.',
      cancel: 'Cancel',
      sendLink: 'Send Reset Link',
      success: 'Password reset instructions sent to your email',
      failed: 'Failed to send reset email'
    },
    confirmLogout: 'Are you sure you want to logout?',
    logoutSuccess: 'Successfully logged out'
  },
  header: {
    title: 'Choco Forest Watch',
    titleShort: 'CFW'
  },
  navigation: {
    projects: {
      name: 'Projects',
      tooltip: 'Select or create a project'
    },
    training: {
      name: 'Train Model',
      tooltip: 'Train Model'
    },
    analysis: {
      name: 'Analysis',
      tooltip: 'Analyze and verify'
    }
  },
  analysis: {
    title: 'Analysis',
    runAnalysis: 'Run Analysis',
    selectArea: 'Select Area'
  },
  training: {
    startTraining: 'Start Training',
    selectPolygons: 'Select Polygons',
    modelSettings: 'Model Settings'
  },
  layers: {
    baseMap: 'Base Map',
    satellite: 'Satellite',
    terrain: 'Terrain'
  },
  notifications: {
    projectLoaded: 'Project loaded successfully',
    aoiSaved: 'AOI saved successfully. You can now start training your model.',
    error: {
      training: 'Error transitioning to training mode'
    }
  }
} 