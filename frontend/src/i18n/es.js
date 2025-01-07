export default {
  common: {
    loading: 'Cargando...',
    error: 'Se produjo un error',
    save: 'Guardar',
    cancel: 'Cancelar',
    showHelp: 'Mostrar Ayuda',
    getStarted: 'Comenzar',
    logout: 'Cerrar Sesión',
    about: 'Acerca de',
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
      loginFailed: 'Error al iniciar sesión',
      about: {
        title: '¿Qué es Choco Forest Watch?',
        description: 'Choco Forest Watch es una plataforma especializada que permite a las comunidades monitorear la deforestación utilizando imágenes satelitales e inteligencia artificial. Nuestra herramienta combina tecnología avanzada con conocimiento local para proteger valiosos ecosistemas forestales.',
        features: {
          title: 'Con Choco Forest Watch, puedes:',
          project: 'Crear Proyectos: Define tus áreas de interés y personaliza las clases de cobertura terrestre según tu contexto local.',
          training: 'Entrenar el Sistema: Proporciona ejemplos de diferentes tipos de cobertura para que la IA comprenda tu paisaje forestal.',
          model: 'Construir Modelos Personalizados: Desarrolla modelos de aprendizaje automático adaptados a tu región y tipos de bosque específicos.',
          analysis: 'Monitorear Cambios: Rastrea patrones de deforestación e identifica áreas que necesitan atención.',
          share: 'Impulsar Acciones: Genera informes detallados y visualizaciones para apoyar esfuerzos de conservación.'
        },
        getStarted: '¿Listo para comenzar? Inicia sesión o crea una nueva cuenta para unirte a nuestra comunidad de guardianes del bosque. Nuestras guías interactivas te ayudarán en cada paso.'
      },
      landing: {
        tagline: "Monitoreo de Deforestación para Conservación Local",
        subtitle: "Plataforma gratuita y de código abierto que potencia los esfuerzos de conservación local con tecnología de vanguardia",
        motivation: "Las iniciativas globales de monitoreo de la deforestación son invaluables, a menudo enfrentan desafíos a escalas locales donde ocurre la mayoría del trabajo de conservación en terreno. Choco Forest Watch cierra esta brecha permitiendo modelos de aprendizaje automático personalizados entrenados con experiencia local.",
        features: {
          title: "Características Principales",
          satellite: {
            title: "Imágenes Satelitales de Alta Resolución",
            description: "Accede a imágenes mensuales de 4.7m de resolución de PlanetLabs a través del Programa NICFI"
          },
          ml: {
            title: "Aprendizaje Automático Personalizado",
            description: "Desarrolla modelos localizados adaptados a tu región y paisaje específico"
          },
          monitoring: {
            title: "Monitoreo Avanzado",
            description: "Genera alertas de deforestación de alta resolución y rastrea cambios en el uso del suelo a lo largo del tiempo"
          }
        },
        funding: {
          title: "Apoyado Por",
          description: "El desarrollo de Choco Forest Watch fue posible gracias al apoyo de:"
        },
        cta: {
          login: "Iniciar Sesión",
          createAccount: "Crear Cuenta Gratuita",
          learnMore: "Más Información"
        }
      }
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
    },
    close: 'Cerrar',
    export: 'Exportar'
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
    selectArea: 'Seleccionar Área',
    unified: {
      deforestation: {
        title: 'Análisis de Deforestación',
        existing: {
          title: 'Análisis Existentes',
          empty: 'No hay análisis de deforestación disponibles. Cree un nuevo análisis abajo.',
          tooltips: {
            delete: 'Eliminar Análisis'
          },
          confirm: {
            title: 'Eliminar Análisis',
            message: '¿Está seguro que desea eliminar este análisis?'
          }
        },
        new: {
          title: 'Nuevo Análisis',
          startDate: 'Fecha de Inicio',
          endDate: 'Fecha Final',
          analyze: 'Analizar'
        }
      },
      hotspots: {
        title: 'Puntos Críticos Detectados',
        count: 'punto crítico | puntos críticos',
        empty: 'No se encontraron puntos críticos en el área seleccionada.',
        export: {
          title: 'Exportar Puntos Críticos',
          all: 'Todos los Puntos Críticos',
          verifiedOnly: 'Solo Verificados'
        },
        filters: {
          minArea: 'Área Mínima (ha)',
          source: 'Fuente de Alerta',
          sources: {
            all: 'Todas las Fuentes',
            local: 'Alertas Locales',
            gfw: 'Global Forest Watch'
          }
        },
        confidence: {
          high: 'Alta',
          medium: 'Media',
          low: 'Baja'
        },
        status: {
          unverified: 'Sin Verificar',
          verified: 'Verificado',
          rejected: 'Rechazado',
          unsure: 'Incierto'
        },
        tooltips: {
          verify: 'Verificar Deforestación',
          unsure: 'Marcar como Incierto',
          reject: 'Rechazar Alerta'
        }
      },
      maps: {
        legend: {
          title: 'Tipos de Alertas',
          local: 'Alerta Local',
          gfw: 'Alerta GFW',
          status: {
            title: 'Estado de Verificación',
            verified: 'Verificado',
            unsure: 'Incierto',
            rejected: 'Rechazado'
          }
        }
      },
      stats: {
        title: 'Estadísticas de Análisis',
        subtitle: '{start} a {end}',
        close: 'Cerrar',
        export: 'Exportar',
        overview: {
          title: 'Resumen por Fuente (Puntos críticos ≥ {minArea} ha)',
          localAlerts: 'Alertas Locales',
          gfwAlerts: 'Alertas GFW',
          showing: 'Mostrando puntos críticos ≥ {minArea} ha',
          hotspots: 'Puntos críticos',
          totalArea: 'Área Total',
          annualRate: 'Tasa Anual',
          haPerYear: 'ha/año',
          percentOfAoi: '{percent}% del AOI'
        },
        breakdown: {
          title: 'Desglose por Estado (Puntos críticos ≥ {minArea} ha)',
          hotspotCount: '{count} puntos críticos',
          percentOfSource: '{percent}% de {source}',
          status: {
            verified: 'Verificado',
            unsure: 'Incierto',
            rejected: 'Rechazado',
            unverified: 'No verificado'
          }
        },
        landCover: {
          title: 'Porcentajes de Cobertura Terrestre',
          types: {
            forest: 'Bosque',
            'non-forest': 'No Bosque',
            water: 'Agua',
            cloud: 'Nube',
            shadow: 'Sombra'
          }
        },
        aoiInfo: 'Los porcentajes de área se calculan en relación con el área total del AOI de {area} ha'
      },
      notifications: {
        projectRequired: 'Por favor seleccione un proyecto primero',
        selectProject: 'Seleccionar Proyecto',
        analysisDeleted: 'Análisis eliminado exitosamente',
        deleteError: 'Error al eliminar el análisis',
        analysisSaved: 'Análisis guardado exitosamente',
        analysisError: 'Error al ejecutar el análisis',
        verificationUpdated: 'Estado de verificación actualizado',
        verificationError: 'Error al actualizar el estado de verificación',
        exportSuccess: 'Exportación completada exitosamente',
        exportError: 'Error al exportar datos'
      },
      dialogs: {
        delete: {
          title: 'Eliminar Análisis',
          message: '¿Está seguro que desea eliminar este análisis?',
          confirm: 'Eliminar',
          cancel: 'Cancelar'
        },
        stats: {
          title: 'Estadísticas de Análisis',
          close: 'Cerrar',
          export: 'Exportar Estadísticas',
          sections: {
            overview: 'Resumen',
            sources: 'Fuentes de Alertas',
            verification: 'Estado de Verificación'
          }
        }
      }
    }
  },
  training: {
    startTraining: 'Iniciar Entrenamiento',
    selectPolygons: 'Seleccionar Polígonos',
    modelSettings: 'Configuración del Modelo',
    modelTraining: {
      title: {
        train: 'Entrenar Modelo XGBoost',
        update: 'Actualizar Modelo XGBoost'
      },
      progress: {
        title: 'Entrenamiento y Predicción en Progreso',
        close: 'Cerrar',
        cancel: 'Cancelar',
        tooltips: {
          cancel: 'Cancelar entrenamiento'
        }
      },
      buttons: {
        cancel: 'Cancelar',
        train: 'Entrenar Modelo',
        update: 'Actualizar Modelo'
      },
      validation: {
        invalidConfig: 'Por favor, asegúrese de que todos los parámetros del modelo sean válidos antes de entrenar',
        oneFeature: 'No se permiten clases con exactamente 1 característica',
        oneFeatureCaption: 'Por favor, agregue al menos una característica más a: {classes}',
        twoClasses: 'Al menos dos clases deben tener datos de entrenamiento',
        twoClassesCaption: 'Por favor, agregue características a al menos una clase más',
        noData: 'No hay datos de entrenamiento disponibles',
        parameterErrors: {
          invalid: 'Valor inválido para {param}',
          estimators: 'El número de estimadores debe ser al menos 10',
          maxDepth: 'La profundidad máxima debe ser al menos 1',
          learningRate: 'La tasa de aprendizaje debe ser mayor que 0',
          minChildWeight: 'El peso mínimo del hijo debe ser al menos 1',
          gamma: 'Gamma debe ser no negativo',
          subsample: 'El submuestreo debe estar entre 0 y 1',
          colsample: 'El colsample bytree debe estar entre 0 y 1'
        }
      },
      dataSummary: {
        totalSets: 'Total de Conjuntos de Entrenamiento',
        totalArea: 'Área Total',
        class: 'Clase',
        features: 'Características',
        area: 'Área (ha)',
        percentage: '%',
        trainingDates: 'Fechas de datos de entrenamiento:'
      },
      parameters: {
        title: 'Parámetros del Modelo',
        caption: 'Haga clic para personalizar los parámetros del modelo',
        modelParams: {
          estimators: {
            title: 'Número de Estimadores',
            description: 'El número de árboles en el bosque. Valores más altos generalmente mejoran el rendimiento pero aumentan el tiempo de entrenamiento.'
          },
          maxDepth: {
            title: 'Profundidad Máxima',
            description: 'Profundidad máxima de los árboles. Valores más altos hacen que el modelo sea más complejo y propenso al sobreajuste.'
          },
          learningRate: {
            title: 'Tasa de Aprendizaje',
            description: 'Reducción del tamaño del paso utilizada para prevenir el sobreajuste. Valores más bajos son generalmente mejores pero requieren más iteraciones.'
          },
          minChildWeight: {
            title: 'Peso Mínimo del Hijo',
            description: 'Suma mínima del peso de instancia necesaria en un hijo. Valores más altos hacen que el modelo sea más conservador.'
          },
          gamma: {
            title: 'Gamma',
            description: 'Reducción mínima de pérdida requerida para hacer una partición adicional. Valores más altos hacen que el modelo sea más conservador.'
          },
          subsample: {
            title: 'Submuestreo',
            description: 'Fracción de muestras utilizadas para ajustar los árboles. Valores más bajos pueden ayudar a prevenir el sobreajuste.'
          },
          colsample: {
            title: 'Muestreo por Columna',
            description: 'Fracción de características utilizadas para construir cada árbol. Puede ayudar a reducir el sobreajuste.'
          }
        },
        splitMethod: {
          title: 'Elija el método de división:',
          feature: 'Basado en características',
          pixel: 'Basado en píxeles',
          featureDescription: 'La división basada en características asegura la independencia entre los datos de entrenamiento y prueba al dividir polígonos completos. La división basada en píxeles puede mezclar píxeles del mismo polígono en ambos conjuntos de entrenamiento y prueba.'
        },
        trainTest: {
          title: 'Ajustar la división entrenamiento/prueba:',
          description: 'Esto determina la proporción de datos utilizada para pruebas. Un valor de {value} significa que el {percent}% de los datos se utilizará para pruebas y el {remaining}% para entrenamiento. Porcentajes más altos de prueba proporcionan estimaciones de precisión más confiables pero dejan menos datos para el entrenamiento, lo que puede llevar al sobreajuste.'
        },
        sieveFilter: {
          title: 'Tamaño del Filtro Tamiz:',
          description: 'Tamaño mínimo de grupos de píxeles conectados para mantener en la predicción final. Valores más altos crean un mapa más generalizado al eliminar parches aislados pequeños. Establezca en 0 para deshabilitar el filtrado.'
        }
      }
    },
    evaluation: {
      title: 'Evaluación del Modelo',
      noMetrics: {
        title: 'No Hay Métricas Disponibles',
        subtitle: 'Por favor, entrene un modelo primero.'
      },
      created: 'Creado',
      updated: 'Actualizado',
      parameters: {
        title: 'Parámetros del Modelo',
        splitMethod: 'Método de División',
        trainTestSplit: 'División Entrenamiento/Prueba',
        estimators: 'Número de Estimadores',
        maxDepth: 'Profundidad Máxima',
        learningRate: 'Tasa de Aprendizaje',
        minChildWeight: 'Peso Mínimo del Hijo',
        sieveSize: 'Tamaño del Filtro Tamiz',
        pixels: 'píxeles',
        subsample: 'Submuestreo'
      },
      metrics: {
        title: 'Métricas de Rendimiento',
        overallAccuracy: 'Precisión General',
        class: 'Clase',
        precision: 'Precisión',
        recall: 'Exhaustividad',
        f1Score: 'Puntuación F1'
      },
      confusionMatrix: {
        title: 'Matriz de Confusión',
        predicted: 'Predicho'
      },
      interpretation: {
        title: 'Interpretación',
        accuracy: 'El modelo alcanza una precisión general del {accuracy}%, lo que significa que clasifica correctamente este porcentaje de todas las muestras de prueba.',
        keyFindings: 'Hallazgos clave por clase:',
        classMetrics: {
          precision: 'Precisión: {value}% de las áreas predichas como {class} son correctas',
          recall: 'Exhaustividad: {value}% de las áreas reales de {class} son identificadas correctamente',
          f1: 'Puntuación F1: {value}% medida de precisión balanceada'
        }
      },
      close: 'Cerrar'
    },
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
    switcher: {
      title: 'Capas',
      opacity: 'Opacidad',
      tooltips: {
        toggleOpacity: 'Ajustar opacidad',
        remove: 'Eliminar capa'
      }
    },
    basemapDate: {
      title: 'Fecha del Mapa Base',
      months: {
        jan: 'Enero',
        feb: 'Febrero',
        mar: 'Marzo',
        apr: 'Abril',
        may: 'Mayo',
        jun: 'Junio',
        jul: 'Julio',
        aug: 'Agosto',
        sep: 'Septiembre',
        oct: 'Octubre',
        nov: 'Noviembre',
        dec: 'Diciembre',
        short: {
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
  },
  welcome: {
    dontShowAgain: "No mostrar de nuevo",
    projects: {
      title: 'Bienvenido a Proyectos',
      intro: 'Los proyectos te ayudan a organizar tu trabajo de monitoreo de deforestación. Aquí te explicamos cómo empezar:',
      create: {
        title: 'Crear un Proyecto',
        description: 'Comienza creando un nuevo proyecto para organizar tu trabajo de monitoreo.'
      },
      aoi: {
        title: 'Definir Área de Interés',
        description: 'Sube o dibuja tu área de interés (AOI) para enfocar tu análisis.'
      },
      configure: {
        title: 'Configurar Ajustes',
        description: 'Configura las clases de cobertura terrestre y otros ajustes específicos del proyecto.'
      }
    },
    training: {
      title: 'Bienvenido al Entrenamiento del Modelo',
      intro: 'Entrena tu propio modelo de detección de deforestación usando aprendizaje automático. Sigue estos pasos:',
      draw: {
        title: 'Dibujar Datos de Entrenamiento',
        description: 'Dibuja o carga polígonos de entrenamiento para identificar bosque, no-bosque y otros tipos de cobertura.'
      },
      configure: {
        title: 'Configurar Ajustes del Modelo',
        description: 'Elige los parámetros del modelo y la configuración de validación para optimizar el rendimiento.'
      },
      train: {
        title: 'Entrenar y Evaluar',
        description: 'Inicia el entrenamiento y monitorea el progreso. Revisa las métricas de precisión al finalizar.'
      }
    },
    analysis: {
      title: 'Bienvenido al Análisis',
      intro: 'Analiza patrones de deforestación y verifica cambios en tu área de interés:',
      run: {
        title: 'Ejecutar Análisis',
        description: 'Genera predicciones y compara cambios de cobertura entre dos fechas.'
      },
      review: {
        title: 'Revisar Puntos Críticos',
        description: 'Examina posibles áreas de deforestación identificadas por el modelo.'
      },
      verify: {
        title: 'Verificar Cambios',
        description: 'Confirma o rechaza los cambios detectados y exporta tus hallazgos.'
      }
    }
  },
  feedback: {
    button: 'Dar Feedback',
    buttonNav: 'Feedback',
    title: 'Enviar Feedback',
    intro: '¡Ayúdanos a mejorar Choco Forest Watch! Comparte tu experiencia, reporta errores o sugiere nuevas funciones.',
    message: 'Tu mensaje',
    messagePlaceholder: 'Por favor, proporciona tanto detalle como sea posible. Para errores, incluye qué estabas haciendo cuando ocurrió el problema.',
    messageRequired: 'Por favor ingresa tu feedback',
    submit: 'Enviar',
    submitSuccess: '¡Gracias por tu feedback!',
    submitError: 'Error al enviar el feedback. Por favor intenta de nuevo.',
    types: {
      bug: 'Reporte de Error',
      feature: 'Solicitud de Función',
      improvement: 'Mejora',
      other: 'Otro'
    }
  },
  about: {
    title: 'Acerca de Choco Forest Watch',
    version: 'Versión',
    description: 'Choco Forest Watch es un proyecto de código abierto. El código está disponible en',
    github: 'GitHub',
    contact: 'Para preguntas, inquietudes o comentarios, por favor contacte a:',
    creditsTitle: 'Créditos y Uso de Datos',
    satellite: {
      title: 'Imágenes Satelitales',
      description: 'Imágenes con derechos de autor 2024 de Planet Labs, Inc. Todo uso está sujeto al',
      license: 'Acuerdo de Licencia de Participante del Programa de Datos Satelitales NICFI'
    },
    alerts: {
      title: 'Alertas de Deforestación',
      description: 'Alertas integradas de Global Forest Watch disponibles bajo',
      license: 'Licencia CC BY 4.0'
    },
    funding: {
      title: 'Financiamiento',
      description: 'Este proyecto fue posible gracias al financiamiento de:',
      sources: {
        gfw: 'Programa de Pequeñas Subvenciones de Global Forest Watch y el World Resources Institute',
        yale: 'Iniciativa de Ciencia de Datos Ambientales de Yale (YEDSI)',
        tulane: 'Centro de Excelencia para la Inteligencia Artificial Comprometida con la Comunidad de Tulane (CEAI)',
        caids: 'Instituto Connolly Alexander de Ciencia de Datos (CAIDS)'
      }
    }
  }
} 