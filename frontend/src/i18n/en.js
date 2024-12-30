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
      failed: 'Failed to send reset email',
      enterNew: 'Enter your new password',
      newPassword: 'New Password',
      confirmPassword: 'Confirm Password',
      passwordRequired: 'Password is required',
      confirmRequired: 'Password confirmation is required',
      passwordsNoMatch: 'Passwords do not match',
      resetButton: 'Reset Password',
      resetSuccess: 'Password reset successful! Please login with your new password.',
      resetFailed: 'Failed to reset password'
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
    modelSettings: 'Model Settings',
    summary: {
      title: 'Training Data Summary',
      features: 'feature',
      features_plural: 'features',
      hectares: 'ha'
    },
    model: {
      title: 'Fit and Evaluate Model',
      fit: 'Fit Model',
      evaluate: 'Evaluate Model',
      notifications: {
        initiated: 'Model training initiated successfully'
      }
    }
  },
  layers: {
    baseMap: 'Base Map',
    satellite: 'Satellite',
    terrain: 'Terrain',
    basemapDate: {
      title: 'Basemap Date',
      months: {
        jan: 'Jan',
        feb: 'Feb',
        mar: 'Mar',
        apr: 'Apr',
        may: 'May',
        jun: 'Jun',
        jul: 'Jul',
        aug: 'Aug',
        sep: 'Sep',
        oct: 'Oct',
        nov: 'Nov',
        dec: 'Dec'
      }
    }
  },
  notifications: {
    projectLoaded: 'Project loaded successfully',
    aoiSaved: 'AOI saved successfully. You can now start training your model.',
    languageUpdated: 'Language preference updated successfully',
    languageUpdateFailed: 'Failed to update language preference',
    error: {
      training: 'Error transitioning to training mode'
    }
  },
  projects: {
    existingProjects: 'Existing Projects',
    createNew: 'Create New Project',
    projectName: 'Project Name',
    description: 'Description',
    createButton: 'Create Project',
    nameRequired: 'Project name is required. Please enter a name for your project.',
    minClasses: 'At least 2 classes are required',
    uniqueClasses: 'Class names must be unique',
    created: 'Project created successfully. Please define your Area of Interest.',
    failedCreate: 'Failed to create project',
    rename: {
      title: 'Rename Project',
      newName: 'New Project Name',
      empty: 'Project name cannot be empty',
      success: 'Project renamed successfully',
      failed: 'Failed to rename project'
    },
    delete: {
      title: 'Confirm Delete',
      confirm: 'Are you sure you want to delete the project "{name}"?',
      success: 'Project deleted successfully',
      failed: 'Failed to delete project'
    },
    table: {
      name: 'Name',
      updated: 'Updated',
      actions: 'Actions'
    },
    tooltips: {
      load: 'Load Project',
      rename: 'Rename Project',
      delete: 'Delete Project'
    },
    buttons: {
      cancel: 'Cancel',
      rename: 'Rename'
    },
    aoi: {
      title: 'Define Area of Interest',
      description: 'Please draw the Area of Interest (AOI) for your project on the map or upload a GeoJSON file or .zipped Shapefile.',
      currentSize: 'Current AOI Size',
      hectares: 'ha',
      sizeWarning: 'Warning: AOI size exceeds the maximum allowed ({max} ha)',
      actions: 'Actions',
      buttons: {
        draw: 'Draw AOI',
        upload: 'Upload AOI file',
        clear: 'Clear AOI',
        save: 'Save AOI'
      },
      tooltips: {
        upload: 'Upload .geojson or zipped shapefile'
      },
      notifications: {
        saved: 'AOI saved successfully',
        saveFailed: 'Failed to save AOI',
        uploadSuccess: 'File uploaded successfully',
        uploadFailed: 'Failed to parse {fileType}',
        unsupportedFile: 'Unsupported file type. Please upload a GeoJSON or a Zipped Shapefile.',
        tooLarge: 'AOI is too large. Maximum allowed area is {max} ha',
        noFeatures: 'No valid features found in the file',
        noAoi: 'No AOI drawn'
      }
    },
    notifications: {
      fetchFailed: 'Failed to fetch projects'
    },
    ok: 'Ok'
  },
  drawing: {
    title: 'Drawing Controls',
    options: {
      title: 'Drawing Options',
      squareMode: 'Square Mode (F)',
      freehandMode: 'Freehand Mode (F)',
      polygonSize: 'Polygon Size (m)'
    },
    modes: {
      draw: 'Draw (D)',
      pan: 'Pan (M)',
      zoomIn: 'Zoom In (Z)',
      zoomOut: 'Zoom Out (X)'
    },
    classes: {
      title: 'Select Class'
    },
    management: {
      title: 'Polygon Management',
      undo: 'Undo (Ctrl+Z)',
      save: 'Save (Ctrl+S)',
      clear: 'Clear',
      delete: 'Delete (Del)',
      download: 'Download',
      load: 'Load',
      includeDate: 'Include Date',
      excludeDate: 'Exclude Date'
    },
    dialogs: {
      delete: {
        title: 'Delete Feature',
        message: 'Are you sure you want to delete this feature?'
      }
    },
    notifications: {
      saveError: 'Error saving training polygons',
      dateIncluded: 'Date has been included',
      dateExcluded: 'Date has been excluded',
      dateToggleError: 'Error toggling date exclusion status',
      noFeatureSelected: 'No feature selected',
      polygonsLoaded: 'Polygons loaded successfully',
      loadError: 'Failed to load polygons from file'
    }
  }
} 