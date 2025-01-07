export default {
  common: {
    loading: 'Loading...',
    error: 'An error occurred',
    save: 'Save',
    cancel: 'Cancel',
    showHelp: 'Show Help',
    getStarted: 'Get Started',
    logout: 'Logout',
    about: 'About',
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
      loginFailed: 'Login failed',
      about: {
        title: 'What is Choco Forest Watch?',
        description: 'Choco Forest Watch is a platform that supports communities to monitor deforestation using satellite imagery and artificial intelligence. Our tool combines cutting-edge technology with local knowledge to protect valuable forest ecosystems.',
        features: {
          title: 'With Choco Forest Watch, you can:',
          project: 'Create Projects: Define your areas of interest and customize land cover classes to match your local context.',
          training: 'Train the System: Provide examples of different land cover types to help the AI understand your forest landscape.',
          model: 'Build Custom Models: Develop machine learning models tailored to your specific region and forest types.',
          analysis: 'Monitor Changes: Track deforestation patterns and identify areas that need attention.',
          share: 'Drive Action: Generate detailed reports and visualizations to support conservation efforts.'
        },
        getStarted: 'Ready to begin? Sign in below or create a new account to join our community of forest guardians. Our interactive guides will help you every step of the way.'
      },
      landing: {
        tagline: "Deforestation Monitoring for Local Conservation",
        subtitle: "Free, open-source platform supporting local conservation efforts",
        motivation: "While global deforestation monitoring initiatives are invaluable, they often face challenges at local scales where most on-the-ground conservation work happens. Choco Forest Watch bridges this gap by enabling custom machine learning models trained with local expertise.",
        features: {
          title: "Key Features",
          satellite: {
            title: "High-Resolution Satellite Imagery",
            description: "View monthly 4.7m resolution imagery from PlanetLabs through the NICFI Program"
          },
          ml: {
            title: "Custom Machine Learning Models",
            description: "Develop localized models tailored to your specific region and landscape"
          },
          monitoring: {
            title: "Advanced Monitoring",
            description: "Generate high-resolution deforestation alerts and track land use changes over time"
          }
        },
        funding: {
          title: "Supported By",
          description: "Choco Forest Watch's development was made possible through the support of:",
          sources: [
            {
              name: "Global Forest Watch Small Grants Program and the World Resources Institute",
              logo: "gfw-logo"
            },
            {
              name: "Yale Environmental Data Science Initiative (YEDSI)",
              logo: "yale-logo"
            },
            {
              name: "Tulane Center of Excellence for Community-Engaged Artificial Intelligence (CEAI)",
              logo: "tulane-logo"
            },
            {
              name: "The Connolly Alexander Institute for Data Science (CAIDS)",
              logo: "caids-logo"
            }
          ]
        },
        cta: {
          login: "Login",
          createAccount: "Create Account",
          learnMore: "Learn More"
        }
      },
      alreadyHaveAccount: 'Already have an account?'
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
      failed: 'Registration failed',
      errors: {
        userExists: 'A user with that username already exists',
        emailExists: 'A user with that email already exists',
        invalidEmail: 'Please enter a valid email address'
      }
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
    logoutSuccess: 'Successfully logged out',
    close: 'Close',
    export: 'Export'
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
    selectArea: 'Select Area',
    unified: {
      deforestation: {
        title: 'Deforestation Analysis',
        existing: {
          title: 'Existing Analyses',
          empty: 'No deforestation analyses available. Create a new analysis below.',
          tooltips: {
            delete: 'Delete Analysis'
          },
          confirm: {
            title: 'Delete Analysis',
            message: 'Are you sure you want to delete this analysis?'
          }
        },
        new: {
          title: 'New Analysis',
          startDate: 'Start Date',
          endDate: 'End Date',
          analyze: 'Analyze'
        }
      },
      hotspots: {
        title: 'Detected Hotspots',
        count: 'hotspot | hotspots',
        empty: 'No hotspots found in the selected area.',
        export: {
          title: 'Export Hotspots',
          all: 'All Hotspots',
          verifiedOnly: 'Verified Only'
        },
        filters: {
          minArea: 'Min Area (ha)',
          source: 'Alert Source',
          sources: {
            all: 'All Sources',
            local: 'Local Alerts',
            gfw: 'Global Forest Watch'
          }
        },
        confidence: {
          high: 'High',
          medium: 'Medium',
          low: 'Low'
        },
        status: {
          unverified: 'Unverified',
          verified: 'Verified',
          rejected: 'Rejected',
          unsure: 'Unsure'
        },
        tooltips: {
          verify: 'Verify Deforestation',
          unsure: 'Mark as Unsure',
          reject: 'Reject Alert'
        }
      },
      maps: {
        legend: {
          title: 'Alert Types',
          local: 'Local Alert',
          gfw: 'GFW Alert',
          status: {
            title: 'Verification Status',
            verified: 'Verified',
            unsure: 'Unsure',
            rejected: 'Rejected'
          }
        }
      },
      stats: {
        title: 'Analysis Statistics',
        subtitle: '{start} to {end}',
        close: 'Close',
        export: 'Export',
        overview: {
          title: 'Overview by Source (Hotspots ≥ {minArea} ha)',
          localAlerts: 'Local Alerts',
          gfwAlerts: 'GFW Alerts',
          showing: 'Showing hotspots ≥ {minArea} ha',
          hotspots: 'Hotspots',
          totalArea: 'Total Area',
          annualRate: 'Annual Rate',
          haPerYear: 'ha/year',
          percentOfAoi: '{percent}% of AOI'
        },
        breakdown: {
          title: 'Status Breakdown by Source (Hotspots ≥ {minArea} ha)',
          hotspotCount: '{count} hotspots',
          percentOfSource: '{percent}% of {source}',
          status: {
            verified: 'Verified',
            unsure: 'Unsure',
            rejected: 'Rejected',
            unverified: 'Unverified'
          }
        },
        landCover: {
          title: 'Land Cover Percentages',
          types: {
            forest: 'Forest',
            'non-forest': 'Non-Forest',
            water: 'Water',
            cloud: 'Cloud',
            shadow: 'Shadow'
          }
        },
        aoiInfo: 'Area percentages are calculated relative to the total AOI area of {area} ha'
      },
      notifications: {
        projectRequired: 'Please select a project first',
        selectProject: 'Select Project',
        analysisDeleted: 'Analysis deleted successfully',
        deleteError: 'Failed to delete analysis',
        analysisSaved: 'Analysis saved successfully',
        analysisError: 'Error running analysis',
        verificationUpdated: 'Verification status updated',
        verificationError: 'Error updating verification status',
        exportSuccess: 'Export completed successfully',
        exportError: 'Error exporting data'
      },
      dialogs: {
        delete: {
          title: 'Delete Analysis',
          message: 'Are you sure you want to delete this analysis?',
          confirm: 'Delete',
          cancel: 'Cancel'
        },
        stats: {
          title: 'Analysis Statistics',
          close: 'Close',
          export: 'Export Statistics',
          sections: {
            overview: 'Overview',
            sources: 'Alert Sources',
            verification: 'Verification Status'
          }
        }
      }
    }
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
      progress: {
        title: 'Training and Prediction in Progress',
        close: 'Close',
        cancel: 'Cancel',
        tooltips: {
          cancel: 'Cancel training'
        }
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
  },
  welcome: {
    dontShowAgain: "Don't show this again",
    projects: {
      title: 'Welcome to Projects',
      intro: 'Projects help you organize your deforestation monitoring work. Here\'s how to get started:',
      create: {
        title: 'Create a Project',
        description: 'Start by creating a new project to organize your monitoring work.'
      },
      aoi: {
        title: 'Define Area of Interest',
        description: 'Upload or draw your area of interest (AOI) to focus your analysis.'
      },
      configure: {
        title: 'Configure Settings',
        description: 'Set up land cover classes and other project-specific settings.'
      }
    },
    training: {
      title: 'Welcome to Model Training',
      intro: 'Train your own deforestation detection model using machine learning. Follow these steps:',
      draw: {
        title: 'Draw Training Data',
        description: 'Draw or upload training polygons to identify forest, non-forest, and other land cover types.'
      },
      configure: {
        title: 'Configure Model Settings',
        description: 'Choose model parameters and validation settings to optimize performance.'
      },
      train: {
        title: 'Train and Evaluate',
        description: 'Start training and monitor progress. Review accuracy metrics when complete.'
      }
    },
    analysis: {
      title: 'Welcome to Analysis',
      intro: 'Analyze deforestation patterns and verify changes in your area of interest:',
      run: {
        title: 'Run Analysis',
        description: 'Generate predictions and compare land cover changes between two dates.'
      },
      review: {
        title: 'Review Hotspots',
        description: 'Examine potential deforestation hotspots identified by the model.'
      },
      verify: {
        title: 'Verify Changes',
        description: 'Confirm or reject detected changes and export your findings.'
      }
    }
  },
  feedback: {
    button: 'Give Feedback',
    buttonNav: 'Feedback',
    title: 'Send Feedback',
    intro: 'Help us improve Choco Forest Watch! Share your experience, report bugs, or suggest new features.',
    message: 'Your message',
    messagePlaceholder: 'Please provide as much detail as possible. For bugs, include what you were doing when the issue occurred.',
    messageRequired: 'Please enter your feedback',
    submit: 'Submit',
    submitSuccess: 'Thank you for your feedback!',
    submitError: 'Failed to submit feedback. Please try again.',
    types: {
      bug: 'Bug Report',
      feature: 'Feature Request',
      improvement: 'Improvement',
      other: 'Other'
    }
  },
  about: {
    title: 'About Choco Forest Watch',
    version: 'Version',
    description: 'Choco Forest Watch is an open-source project. The code is available on',
    github: 'GitHub',
    contact: 'For questions, concerns, or feedback, please contact:',
    creditsTitle: 'Credits and Data Use',
    satellite: {
      title: 'Satellite Imagery',
      description: 'Imagery copyright 2024 from Planet Labs, Inc. All use is subject to the',
      license: 'NICFI Satellite Data Program Participant License Agreement'
    },
    alerts: {
      title: 'Deforestation Alerts',
      description: 'Global Forest Watch integrated alerts available under',
      license: 'CC BY 4.0 License'
    },
    funding: {
      title: 'Funding',
      description: 'This project was made possible by funding from:',
      sources: {
        gfw: 'Global Forest Watch Small Grants Program and the World Resources Institute',
        yale: 'Yale Environmental Data Science Initiative (YEDSI)',
        tulane: 'Tulane Center of Excellence for Community-Engaged Artificial Intelligence (CEAI)',
        caids: 'The Connolly Alexander Institute for Data Science (CAIDS)'
      }
    }
  }
} 