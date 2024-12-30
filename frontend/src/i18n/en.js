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
    modelTraining: {
      title: {
        train: 'Train XGBoost Model',
        update: 'Update XGBoost Model'
      },
      buttons: {
        cancel: 'Cancel',
        train: 'Train Model',
        update: 'Update Model'
      },
      validation: {
        invalidConfig: 'Please ensure all model parameters are valid before training',
        oneFeature: 'Classes with exactly 1 feature are not allowed',
        oneFeatureCaption: 'Please add at least one more feature to: {classes}',
        twoClasses: 'At least two classes must have training data',
        twoClassesCaption: 'Please add features to at least one more class',
        noData: 'No training data available',
        parameterErrors: {
          invalid: 'Invalid value for {param}',
          estimators: 'Number of estimators must be at least 10',
          maxDepth: 'Max depth must be at least 1',
          learningRate: 'Learning rate must be greater than 0',
          minChildWeight: 'Min child weight must be at least 1',
          gamma: 'Gamma must be non-negative',
          subsample: 'Subsample must be between 0 and 1',
          colsample: 'Colsample bytree must be between 0 and 1'
        }
      },
      dataSummary: {
        totalSets: 'Total Training Sets',
        totalArea: 'Total Area',
        class: 'Class',
        features: 'Features',
        area: 'Area (ha)',
        percentage: '%',
        trainingDates: 'Training data dates:'
      },
      parameters: {
        title: 'Model Parameters',
        caption: 'Click to customize model parameters',
        modelParams: {
          estimators: {
            title: 'Number of Estimators',
            description: 'The number of trees in the forest. Higher values generally improve performance but increase training time.'
          },
          maxDepth: {
            title: 'Max Depth',
            description: 'Maximum depth of the trees. Higher values make the model more complex and prone to overfitting.'
          },
          learningRate: {
            title: 'Learning Rate',
            description: 'Step size shrinkage used to prevent overfitting. Lower values are generally better but require more iterations.'
          },
          minChildWeight: {
            title: 'Min Child Weight',
            description: 'Minimum sum of instance weight needed in a child. Higher values make the model more conservative.'
          },
          gamma: {
            title: 'Gamma',
            description: 'Minimum loss reduction required to make a further partition. Higher values make the model more conservative.'
          },
          subsample: {
            title: 'Subsample',
            description: 'Fraction of samples used for fitting the trees. Lower values can help prevent overfitting.'
          },
          colsample: {
            title: 'Colsample Bytree',
            description: 'Fraction of features used for building each tree. Can help in reducing overfitting.'
          }
        },
        splitMethod: {
          title: 'Choose split method:',
          feature: 'Feature-based',
          pixel: 'Pixel-based',
          featureDescription: 'Feature-based split ensures independence between training and testing data by splitting entire polygons. Pixel-based split may mix pixels from the same polygon in both training and testing sets.'
        },
        trainTest: {
          title: 'Adjust the train/test split:',
          description: 'This determines the proportion of data used for testing. A value of {value} means {percent}% of the data will be used for testing and {remaining}% for training. Higher test percentages provide more reliable accuracy estimates but leave less data for training, which may lead to overfitting.'
        },
        sieveFilter: {
          title: 'Sieve Filter Size:',
          description: 'Minimum size of connected pixel groups to keep in the final prediction. Higher values create a more generalized map by removing small isolated patches. Set to 0 to disable filtering.'
        }
      }
    },
    evaluation: {
      title: 'Model Evaluation',
      noMetrics: {
        title: 'No Model Metrics Available',
        subtitle: 'Please train a model first.'
      },
      created: 'Created',
      updated: 'Updated',
      parameters: {
        title: 'Model Parameters',
        splitMethod: 'Split Method',
        trainTestSplit: 'Train/Test Split',
        estimators: 'Number of Estimators',
        maxDepth: 'Max Depth',
        learningRate: 'Learning Rate',
        minChildWeight: 'Min Child Weight',
        sieveSize: 'Sieve Filter Size',
        pixels: 'pixels',
        subsample: 'Subsample'
      },
      metrics: {
        title: 'Performance Metrics',
        overallAccuracy: 'Overall Accuracy',
        class: 'Class',
        precision: 'Precision',
        recall: 'Recall',
        f1Score: 'F1 Score'
      },
      confusionMatrix: {
        title: 'Confusion Matrix',
        predicted: 'Predicted'
      },
      interpretation: {
        title: 'Interpretation',
        accuracy: 'The model achieves an overall accuracy of {accuracy}%, meaning it correctly classifies this percentage of all test samples.',
        keyFindings: 'Key findings per class:',
        classMetrics: {
          precision: 'Precision: {value}% of areas predicted as {class} are correct',
          recall: 'Recall: {value}% of actual {class} areas are correctly identified',
          f1: 'F1 Score: {value}% balanced accuracy measure'
        }
      },
      close: 'Close'
    },
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
    switcher: {
      title: 'Layers',
      opacity: 'Opacity',
      tooltips: {
        toggleOpacity: 'Toggle opacity control',
        remove: 'Remove layer'
      }
    },
    basemapDate: {
      title: 'Basemap Date',
      months: {
        jan: 'January',
        feb: 'February',
        mar: 'March',
        apr: 'April',
        may: 'May',
        jun: 'June',
        jul: 'July',
        aug: 'August',
        sep: 'September',
        oct: 'October',
        nov: 'November',
        dec: 'December',
        short: {
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