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
    modelSettings: 'Configuración del Modelo',
    summary: {
      title: 'Resumen de Datos de Entrenamiento',
      features: 'característica',
      features_plural: 'características',
      hectares: 'ha'
    },
    model: {
      title: 'Ajustar y Evaluar Modelo',
      fit: 'Ajustar Modelo',
      evaluate: 'Evaluar Modelo',
      notifications: {
        initiated: 'Entrenamiento del modelo iniciado exitosamente'
      }
    }
  },
  layers: {
    baseMap: 'Mapa Base',
    satellite: 'Satélite',
    terrain: 'Terreno',
    basemapDate: {
      title: 'Fecha del Mapa Base',
      months: {
        jan: 'Ene',
        feb: 'Feb',
        mar: 'Mar',
        apr: 'Abr',
        may: 'May',
        jun: 'Jun',
        jul: 'Jul',
        aug: 'Ago',
        sep: 'Sep',
        oct: 'Oct',
        nov: 'Nov',
        dec: 'Dic'
      }
    }
  },
  notifications: {
    projectLoaded: 'Proyecto cargado exitosamente',
    aoiSaved: 'AOI guardado exitosamente. Ahora puede comenzar a entrenar su modelo.',
    languageUpdated: 'Preferencia de idioma actualizada exitosamente',
    languageUpdateFailed: 'Error al actualizar la preferencia de idioma',
    error: {
      training: 'Error al transicionar al modo de entrenamiento'
    }
  },
  projects: {
    existingProjects: 'Proyectos Existentes',
    createNew: 'Crear Nuevo Proyecto',
    projectName: 'Nombre del Proyecto',
    description: 'Descripción',
    createButton: 'Crear Proyecto',
    nameRequired: 'El nombre del proyecto es requerido. Por favor ingrese un nombre para su proyecto.',
    minClasses: 'Se requieren al menos 2 clases',
    uniqueClasses: 'Los nombres de las clases deben ser únicos',
    created: 'Proyecto creado exitosamente. Por favor defina su Área de Interés.',
    failedCreate: 'Error al crear el proyecto',
    rename: {
      title: 'Renombrar Proyecto',
      newName: 'Nuevo Nombre del Proyecto',
      empty: 'El nombre del proyecto no puede estar vacío',
      success: 'Proyecto renombrado exitosamente',
      failed: 'Error al renombrar el proyecto'
    },
    delete: {
      title: 'Confirmar Eliminación',
      confirm: '¿Está seguro que desea eliminar el proyecto "{name}"?',
      success: 'Proyecto eliminado exitosamente',
      failed: 'Error al eliminar el proyecto'
    },
    table: {
      name: 'Nombre',
      updated: 'Actualizado',
      actions: 'Acciones'
    },
    tooltips: {
      load: 'Cargar Proyecto',
      rename: 'Renombrar Proyecto',
      delete: 'Eliminar Proyecto'
    },
    buttons: {
      cancel: 'Cancelar',
      rename: 'Renombrar'
    },
    aoi: {
      title: 'Definir Área de Interés',
      description: 'Por favor dibuje el Área de Interés (AOI) para su proyecto en el mapa o cargue un archivo GeoJSON o Shapefile comprimido.',
      currentSize: 'Tamaño Actual del AOI',
      hectares: 'ha',
      sizeWarning: 'Advertencia: El tamaño del AOI excede el máximo permitido ({max} ha)',
      actions: 'Acciones',
      buttons: {
        draw: 'Dibujar AOI',
        upload: 'Cargar archivo AOI',
        clear: 'Limpiar AOI',
        save: 'Guardar AOI'
      },
      tooltips: {
        upload: 'Cargar archivo .geojson o shapefile comprimido'
      },
      notifications: {
        saved: 'AOI guardado exitosamente',
        saveFailed: 'Error al guardar AOI',
        uploadSuccess: 'Archivo cargado exitosamente',
        uploadFailed: 'Error al procesar {fileType}',
        unsupportedFile: 'Tipo de archivo no soportado. Por favor cargue un archivo GeoJSON o Shapefile comprimido.',
        tooLarge: 'El AOI es demasiado grande. El área máxima permitida es {max} ha',
        noFeatures: 'No se encontraron características válidas en el archivo',
        noAoi: 'No se ha dibujado ningún AOI'
      }
    },
    notifications: {
      fetchFailed: 'Error al cargar los proyectos'
    },
    ok: 'Aceptar'
  },
  drawing: {
    title: 'Controles de Dibujo',
    options: {
      title: 'Opciones de Dibujo',
      squareMode: 'Modo Cuadrado (F)',
      freehandMode: 'Modo Mano Libre (F)',
      polygonSize: 'Tamaño del Polígono (m)'
    },
    modes: {
      draw: 'Dibujar (D)',
      pan: 'Desplazar (M)',
      zoomIn: 'Acercar (Z)',
      zoomOut: 'Alejar (X)'
    },
    classes: {
      title: 'Seleccionar Clase'
    },
    management: {
      title: 'Gestión de Polígonos',
      undo: 'Deshacer (Ctrl+Z)',
      save: 'Guardar (Ctrl+S)',
      clear: 'Limpiar',
      delete: 'Eliminar (Del)',
      download: 'Descargar',
      load: 'Cargar',
      includeDate: 'Incluir Fecha',
      excludeDate: 'Excluir Fecha'
    },
    dialogs: {
      delete: {
        title: 'Eliminar Característica',
        message: '¿Está seguro que desea eliminar esta característica?'
      }
    },
    notifications: {
      saveError: 'Error al guardar los polígonos de entrenamiento',
      dateIncluded: 'Fecha ha sido incluida',
      dateExcluded: 'Fecha ha sido excluida',
      dateToggleError: 'Error al cambiar el estado de exclusión de la fecha',
      noFeatureSelected: 'Ninguna característica seleccionada',
      polygonsLoaded: 'Polígonos cargados exitosamente',
      loadError: 'Error al cargar polígonos desde el archivo'
    }
  }
} 