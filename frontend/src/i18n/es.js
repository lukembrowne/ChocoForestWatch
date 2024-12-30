export default {
  common: {
    loading: 'Cargando...',
    error: 'Se produjo un error',
    save: 'Guardar',
    cancel: 'Cancelar',
    logout: 'Cerrar Sesión',
    confirmLogout: '¿Está seguro que desea cerrar sesión?',
    logoutSuccess: 'Sesión cerrada exitosamente',
    login: {
      title: 'Choco Forest Watch',
      subtitle: 'Monitoree y analice los cambios en la cobertura forestal utilizando imágenes satelitales e inteligencia artificial',
      username: 'Usuario',
      password: 'Contraseña',
      rememberMe: 'Recordarme',
      forgotPassword: '¿Olvidó su contraseña?',
      loginButton: 'Iniciar Sesión',
      noAccount: '¿No tiene una cuenta?',
      createAccount: 'Crear Cuenta',
      usernameRequired: 'El usuario es requerido',
      passwordRequired: 'La contraseña es requerida',
      loginSuccess: 'Sesión iniciada exitosamente',
      loginFailed: 'Error al iniciar sesión'
    },
    register: {
      title: 'Crear Cuenta',
      subtitle: 'Únase a Choco Forest Watch',
      email: 'Correo electrónico',
      emailRequired: 'El correo electrónico es requerido',
      invalidEmail: 'Correo electrónico inválido',
      preferredLanguage: 'Idioma preferido',
      createButton: 'Crear Cuenta',
      success: '¡Cuenta creada exitosamente!',
      failed: 'Error al crear la cuenta'
    },
    resetPassword: {
      title: 'Restablecer Contraseña',
      instructions: 'Ingrese su correo electrónico y le enviaremos instrucciones para restablecer su contraseña.',
      cancel: 'Cancelar',
      sendLink: 'Enviar Link',
      success: 'Instrucciones enviadas a su correo electrónico',
      failed: 'Error al enviar el correo electrónico',
      enterNew: 'Ingrese su nueva contraseña',
      newPassword: 'Nueva Contraseña',
      confirmPassword: 'Confirmar Contraseña',
      passwordRequired: 'La contraseña es requerida',
      confirmRequired: 'La confirmación de contraseña es requerida',
      passwordsNoMatch: 'Las contraseñas no coinciden',
      resetButton: 'Restablecer Contraseña',
      resetSuccess: '¡Contraseña restablecida exitosamente! Por favor inicie sesión con su nueva contraseña.',
      resetFailed: 'Error al restablecer la contraseña'
    }
  },
  header: {
    title: 'Choco Forest Watch',
    titleShort: 'CFW'
  },
  navigation: {
    projects: {
      name: 'Proyectos',
      tooltip: 'Seleccionar o crear proyecto'
    },
    training: {
      name: 'Entrenar Modelo',
      tooltip: 'Entrenar Modelo'
    },
    analysis: {
      name: 'Análisis',
      tooltip: 'Analizar y verificar'
    }
  },
  analysis: {
    title: 'Análisis',
    runAnalysis: 'Ejecutar Análisis',
    selectArea: 'Seleccionar Área'
  },
  training: {
    startTraining: 'Iniciar Entrenamiento',
    selectPolygons: 'Seleccionar Polígonos',
    modelSettings: 'Configuración del Modelo'
  },
  layers: {
    baseMap: 'Mapa Base',
    satellite: 'Satélite',
    terrain: 'Terreno'
  },
  notifications: {
    projectLoaded: 'Proyecto cargado exitosamente',
    aoiSaved: 'AOI guardado exitosamente. Ahora puede comenzar a entrenar su modelo.',
    error: {
      training: 'Error al transicionar al modo de entrenamiento'
    }
  }
} 