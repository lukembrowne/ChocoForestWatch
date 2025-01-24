<template>
  <q-layout view="hHh LpR fFf">
    <q-header class="modern-header">
      <q-toolbar class="q-px-lg">
        <div class="header-title">
          <q-avatar size="24px" class="q-mr-sm">
            <img src="/images/favicon-32x32.png" alt="logo">
          </q-avatar>
          <span class="gt-xs">{{ t('header.title') }}</span>
          <span class="lt-sm">{{ t('header.titleShort') }}</span>
        </div>
        
        <div class="flex-grow" />
        
        <div class="nav-section row items-center no-wrap q-gutter-x-md">
          <q-btn 
            v-for="section in sections" 
            :key="section.name" 
            flat 
            :icon="section.icon" 
            :label="$q.screen.gt.xs ? t(`navigation.${section.id}.name`) : ''"
            class="nav-btn"
            @click="handleSectionClick(section)">
            <q-tooltip>{{ t(`navigation.${section.id}.tooltip`) }}</q-tooltip>
          </q-btn>
          <q-btn
            flat
            icon="feedback"
            :label="$q.screen.gt.xs ? t('feedback.buttonNav') : ''"
            class="nav-btn"
            @click="showFeedbackDialog = true"
          >
            <q-tooltip>{{ t('feedback.button') }}</q-tooltip>
          </q-btn>
        </div>

        <!-- User menu -->
        <q-btn-dropdown 
          flat 
          :icon="currentUser ? 'account_circle' : 'login'"
          class="user-menu-btn q-ml-lg" 
          v-if="currentUser"
          size="sm"
        >
          <q-list class="modern-menu">
            <q-item class="text-center">
              <q-item-section>
                <div class="row items-center">
                  <q-avatar size="48px" color="primary" text-color="white">
                    {{ currentUser.user.username.charAt(0).toUpperCase() }}
                  </q-avatar>
                  <div class="text-subtitle2 q-ml-sm">{{ currentUser.user.username }}</div>
                </div>
              </q-item-section>
            </q-item>

            <q-separator />

            <q-item>
              <q-item-section avatar>
                <q-icon name="language" />
              </q-item-section>
              <q-item-section>
                <div class="row q-gutter-sm">
                  <q-radio
                    v-model="currentLocale"
                    val="en"
                    label="English"
                    color="primary"
                    @update:model-value="handleLocaleChange"
                  />
                  <q-radio
                    v-model="currentLocale"
                    val="es"
                    label="Español"
                    color="primary"
                    @update:model-value="handleLocaleChange"
                  />
                </div>
              </q-item-section>
            </q-item>

            <q-item clickable v-ripple @click="showHelp">
              <q-item-section avatar>
                <q-icon name="help" />
              </q-item-section>
              <q-item-section>{{ t('common.showHelp') }}</q-item-section>
            </q-item>

            <q-item clickable v-ripple @click="showAboutDialog = true">
              <q-item-section avatar>
                <q-icon name="info" />
              </q-item-section>
              <q-item-section>{{ t('common.about') }}</q-item-section>
            </q-item>

            <q-item clickable v-ripple @click="handleLogout">
              <q-item-section avatar>
                <q-icon name="logout" />
              </q-item-section>
              <q-item-section>{{ t('common.logout') }}</q-item-section>
            </q-item>

           
          </q-list>
        </q-btn-dropdown>
      </q-toolbar>
    </q-header>

    <q-page-container class="q-pa-none">
      <q-page class="relative-position">
        <div class="z-layers">
          <div id="map" class="map-container" :class="{ 'with-sidebar': showAnyPanel || showAOICard }" v-if="!showUnifiedAnalysis && !showAdminDashboard"></div>
          <div class="sidebar-container" v-if="(showAnyPanel || showAOICard) && !showUnifiedAnalysis && !showAdminDashboard">
            <ProjectSelection 
              v-if="showProjectSelection" 
              @project-selected="selectProject"
            />
            <AOIFloatingCard 
              v-if="showAOICard" 
              @aoi-saved="handleAOISaved"
            />
            <TrainingAndPolygonManager v-if="showTrainingAndPolygonManager" />
          </div>
          <UnifiedAnalysis v-if="showUnifiedAnalysis" />
          <SystemDashboard v-if="showAdminDashboard" />
          <div class="floating-elements" v-if="!showAOICard && !showUnifiedAnalysis && !showAdminDashboard">
            <BasemapDateSlider class="date-slider" />
          </div>
          <custom-layer-switcher v-if="!showUnifiedAnalysis && !showAdminDashboard" mapId="training" />
        </div>
      </q-page>
    </q-page-container>

    <q-dialog v-model="showFeedbackDialog">
      <q-card style="width: 500px; max-width: 90vw;">
        <q-card-section class="bg-primary text-white">
          <div class="text-h6">{{ t('feedback.title') }}</div>
        </q-card-section>

        <q-card-section>
          <p class="text-body1 q-mb-md">{{ t('feedback.intro') }}</p>
          <q-form @submit="submitFeedback" class="q-gutter-md">
            <div class="row q-col-gutter-sm">
              <div class="col-12">
                <q-option-group
                  v-model="feedbackType"
                  :options="feedbackOptions"
                  color="primary"
                  inline
                />
              </div>

              <div class="col-12">
                <q-input
                  v-model="feedbackMessage"
                  type="textarea"
                  :label="t('feedback.message')"
                  :placeholder="t('feedback.messagePlaceholder')"
                  filled
                  autogrow
                  rows="6"
                  class="feedback-textarea"
                  :rules="[val => !!val || t('feedback.messageRequired')]"
                />
              </div>
            </div>

            <div class="row justify-end q-gutter-sm">
              <q-btn flat :label="t('common.cancel')" v-close-popup />
              <q-btn 
                type="submit" 
                color="primary"
                :label="t('feedback.submit')"
                :loading="submittingFeedback"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="showAboutDialog">
      <q-card class="modern-menu" style="width: 700px">
        <q-card-section>
          <div class="text-h6">{{ t('about.title') }}</div>
        </q-card-section>

        <q-card-section>
          <p>{{ t('about.description') }} 
            <a href="https://github.com/lukembrowne/chocoforestwatch" target="_blank">{{ t('about.github') }}</a>.
          </p>

          <div class="disclaimer q-mt-md">
            <div class="text-subtitle2 q-mb-sm">{{ t('about.disclaimer.title') }}</div>
            <p class="text-caption">{{ t('about.disclaimer.text') }}</p>
          </div>

          <div class="q-mt-md">
            <div class="text-subtitle2 q-mb-sm">{{ t('about.creditsTitle') }}</div>
            
            <p class="text-body1">
              <strong>{{ t('about.satellite.title') }}:</strong><br>
              {{ t('about.satellite.description') }}
              <a href="https://planet.widen.net/s/zfdpf8qxwk/participantlicenseagreement_nicfi_2024" target="_blank">
                {{ t('about.satellite.license') }}
              </a>.
            </p>

            <p class="text-body1">
              <strong>{{ t('about.alerts.title') }}:</strong><br>
              {{ t('about.alerts.description') }}
              <a href="https://data.globalforestwatch.org/datasets/gfw::integrated-deforestation-alerts/about" target="_blank">
                {{ t('about.alerts.license') }}
              </a>.
            </p>

            <p class="text-body1">
              <strong>{{ t('about.funding.title') }}:</strong><br>
              {{ t('about.funding.description') }}
              <ul>
                <li>{{ t('about.funding.sources.gfw') }}</li>
                <li>{{ t('about.funding.sources.yale') }}</li>
                <li>{{ t('about.funding.sources.tulane') }}</li>
                <li>{{ t('about.funding.sources.caids') }}</li>
              </ul>
            </p>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import ProjectSelection from 'components/projects/ProjectSelectionDialog.vue'
import TrainingAndPolygonManager from 'components/training/TrainingAndPolygonManager.vue'
import CustomLayerSwitcher from 'components/CustomLayerSwitcher.vue'
import AOIFloatingCard from 'components/projects/AOIFloatingCard.vue'
import BasemapDateSlider from 'components/BasemapDateSlider.vue'
import UnifiedAnalysis from 'components/analysis/UnifiedAnalysis.vue'
import { useRouter, useRoute } from 'vue-router'
import authService from '../services/auth'
import api from '../services/api'
import { GeoJSON } from 'ol/format'
import { useI18n } from 'vue-i18n'
import { useWelcomeStore } from 'src/stores/welcomeStore'
import SystemDashboard from 'src/components/admin/SystemDashboard.vue'


export default {
  name: 'MainLayout',
  components: {
    TrainingAndPolygonManager,
    CustomLayerSwitcher,
    AOIFloatingCard,
    BasemapDateSlider,
    ProjectSelection,
    UnifiedAnalysis,
    SystemDashboard
  },
  setup() {
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const mapStore = useMapStore()
    const currentSection = ref('aoi')
    const currentProject = computed(() => projectStore.currentProject)
    const showAOICard = ref(false)
    const showTrainingAndPolygonManager = ref(false)
    const showLandCoverAnalysis = ref(false)
    const showDeforestationAnalysis = ref(false)
    const showHotspotVerification = ref(false)
    const showProjectSelection = ref(false)
    const showUnifiedAnalysis = ref(false)
    const showAdminDashboard = ref(false)
    const sections = computed(() => {
      const baseSections = [
        { id: 'projects', name: 'projects', icon: 'folder', component: null },
        { id: 'training', name: 'Train Model', icon: 'school', component: TrainingAndPolygonManager },
        { id: 'analysis', name: 'Analysis', icon: 'analytics', component: UnifiedAnalysis }
      ];

      // Add admin dashboard for superusers
      if (currentUser.value?.user?.is_superuser) {
        baseSections.push({
          id: 'admin',
          name: 'Admin Dashboard',
          icon: 'dashboard',
          component: SystemDashboard
        });
      }

      return baseSections;
    })

    const sidebarWidth = computed(() => isExpanded.value ? 300 : 60)
    const currentSectionComponent = computed(() =>
      sections.value.find(s => s.name === currentSection.value)?.component
    )

    const router = useRouter()
    const currentUser = computed(() => authService.getCurrentUser())

    const showAnyPanel = computed(() => 
      showProjectSelection.value || 
      showTrainingAndPolygonManager.value || 
      showUnifiedAnalysis.value || 
      showLandCoverAnalysis.value || 
      showDeforestationAnalysis.value || 
      showHotspotVerification.value ||
      showAdminDashboard.value
    )

    const { t, locale } = useI18n()
    const currentLocale = ref('en')

    const route = useRoute();
    const welcomeStore = useWelcomeStore();

    const showHelp = () => {
      
      if (showProjectSelection.value) {
        welcomeStore.showHelp('projects');
      } else if (showTrainingAndPolygonManager.value) {
        welcomeStore.showHelp('training');
      } else if (showUnifiedAnalysis.value) {
        welcomeStore.showHelp('analysis');
      }
      console.log('Component visibility:', {
        projects: showProjectSelection.value,
        training: showTrainingAndPolygonManager.value,
        analysis: showUnifiedAnalysis.value
      });
    };

    const version = ref('')
    const showAboutDialog = ref(false)

    onMounted(async () => {
      console.log("Mounted MainLayout")
      try {
        // Get version
        const versionResponse = await api.getVersion()
        version.value = versionResponse.data.version

        // Load user settings first
        const { data } = await api.getUserSettings()
        if (data.preferred_language) {
          currentLocale.value = data.preferred_language
          locale.value = data.preferred_language
        }
      } catch (error) {
        console.error('Error in mounted:', error)
      }

      // Standard loading sequence
      // Initialize map
      console.log("Initializing map")
      mapStore.initMap('map', true)
      mapStore.initializeBasemapDates()
      // mapStore.showSingleMap('map')
      showProjectSelection.value = true
    })

    const handleSectionClick = async (section) => {
      // Reset all show flags
      showProjectSelection.value = false;
      showTrainingAndPolygonManager.value = false;
      showUnifiedAnalysis.value = false;
      showLandCoverAnalysis.value = false;
      showDeforestationAnalysis.value = false;
      showHotspotVerification.value = false;
      showAdminDashboard.value = false;

      if (section.name === 'projects') {
        showProjectSelection.value = true;
      } else if (section.name === 'Train Model') {
        showTrainingAndPolygonManager.value = true;
      } else if (section.name === 'Analysis') {
        showUnifiedAnalysis.value = true;
      } else if (section.name === 'Admin Dashboard') {
        showAdminDashboard.value = true;
      } else if (section.name === 'Land Cover') {
        showLandCoverAnalysis.value = true;
      } else if (section.name === 'Deforestation') {
        showDeforestationAnalysis.value = true;
      } else if (section.name === 'Verify Hotspots') {
        showHotspotVerification.value = true;
      }
    }

    const selectProject = async (project) => {
      // Clear existing AOIs
      mapStore.clearAOI()

      console.log("Loading project", project)
      await projectStore.loadProject(project.id)

      if (project.isNew || !projectStore.currentProject.aoi) {
        console.log("New project or no AOI, showing AOI card")
        showProjectSelection.value = false
        showAOICard.value = true
        currentSection.value = null
      } else {
        // Clear AOI
        showAOICard.value = false
        showProjectSelection.value = false

        // Set default basemap after loading a project
        mapStore.updateBasemap('2022-01')

        // Load training polygons for the current date
        mapStore.loadTrainingPolygonsForDate('2022-01')

        // Switching to Train Model section
        handleSectionClick({ name: 'Train Model' })

        // Notify user
        $q.notify({
          message: 'Project loaded successfully',
          color: 'positive',
          icon: 'check'
        })
      }
    }


    const handleAOISaved = async (eventData) => {
      console.log('AOI saved event received in MainLayout with data:', eventData)
      
      try {
        // Hide AOI card first
        showAOICard.value = false
        
        // Wait a tick for UI update
        await nextTick()
        
        // Show training manager
        showTrainingAndPolygonManager.value = true
        currentSection.value = 'Train Model'
        
        // Wait for project AOI to be available
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // Set initial basemap date and zoom to AOI
        const initialDate = '2022-01'
        await Promise.all([
          mapStore.updateBasemap(initialDate),
          mapStore.loadTrainingPolygonsForDate(initialDate),
          mapStore.displayAOI(projectStore.currentProject.aoi)
        ])
        
        // Zoom to AOI extent
        if (projectStore.currentProject?.aoi) {
          const aoiFeature = new GeoJSON().readFeature(projectStore.currentProject.aoi)
          const extent = aoiFeature.getGeometry().getExtent()
          mapStore.map.getView().fit(extent, { 
            padding: [50, 50, 50, 50],
            duration: 1000
          })
        }
        
        $q.notify({
          message: t('notifications.aoiSaved'),
          color: 'positive',
          icon: 'check',
          timeout: 3000
        })
      } catch (error) {
        console.error('Error in handleAOISaved:', error)
        $q.notify({
          message: t('notifications.error.training'),
          color: 'negative',
          icon: 'error'
        })
      }
    }


    const handleLogout = () => {
      $q.dialog({
        title: t('common.logout'),
        message: t('common.confirmLogout'),
        cancel: true,
        persistent: true
      }).onOk(() => {
        authService.logout()
        router.push('/login')
        $q.notify({
          message: t('common.logoutSuccess'),
          color: 'positive',
          icon: 'logout'
        })
      })
    }

    const handleLocaleChange = async (newLocale) => {
      try {
        await api.updateUserSettings({ preferred_language: newLocale })
        locale.value = newLocale
        $q.notify({
          message: t('notifications.languageUpdated'),
          color: 'positive',
          icon: 'check'
        })
      } catch (error) {
        console.error('Error updating language:', error)
        $q.notify({
          message: t('notifications.languageUpdateFailed'),
          color: 'negative',
          icon: 'error'
        })
      }
    }

    // Add feedback related refs and functions
    const showFeedbackDialog = ref(false)
    const feedbackType = ref('bug')
    const feedbackMessage = ref('')
    const submittingFeedback = ref(false)

    const feedbackOptions = [
      { label: t('feedback.types.bug'), value: 'bug' },
      { label: t('feedback.types.feature'), value: 'feature' },
      { label: t('feedback.types.improvement'), value: 'improvement' },
      { label: t('feedback.types.other'), value: 'other' }
    ]

    const getBrowserInfo = () => ({
      userAgent: navigator.userAgent,
      language: navigator.language,
      platform: navigator.platform,
      screenSize: `${window.screen.width}x${window.screen.height}`,
      windowSize: `${window.innerWidth}x${window.innerHeight}`,
      url: window.location.href,
      path: window.location.pathname
    })

    const submitFeedback = async () => {
      try {
        submittingFeedback.value = true
        await api.submitFeedback({
          type: feedbackType.value,
          message: feedbackMessage.value,
          pageUrl: window.location.href,
          user_id: currentUser.value.user.id,
          user_name: currentUser.value.user.username,
          user_email: currentUser.value.user.email,
          project: currentProject.value.id,
          browserInfo: {
            ...getBrowserInfo(),
          }
        })

        $q.notify({
          type: 'positive',
          message: t('feedback.submitSuccess')
        })
        showFeedbackDialog.value = false
        feedbackMessage.value = ''
      } catch (error) {
        console.error('Error submitting feedback:', error)
        $q.notify({
          type: 'negative',
          message: t('feedback.submitError')
        })
      } finally {
        submittingFeedback.value = false
      }
    }

    const testSentryError = () => {
      throw new Error('Test Sentry Error from Frontend');
    }

    return {
      currentSection,
      sections,
      sidebarWidth,
      currentSectionComponent,
      currentProject,
      showAOICard,
      showTrainingAndPolygonManager,
      handleSectionClick,
      handleAOISaved,
      showLandCoverAnalysis,
      showDeforestationAnalysis,
      showHotspotVerification,
      currentUser,
      handleLogout,
      currentLocale,
      t,
      handleLocaleChange,
      showProjectSelection,
      selectProject,
      showAnyPanel,
      showUnifiedAnalysis,
      showHelp,
      showFeedbackDialog,
      feedbackType,
      feedbackMessage,
      submittingFeedback,
      feedbackOptions,
      submitFeedback,
      version,
      showAboutDialog,
      testSentryError,
      showAdminDashboard
    }
  }
}
</script>

<style lang="scss">
.modern-header {
  background: var(--primary-color);
  color: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  height: var(--app-header-height);
}

.header-title {
  font-size: var(--font-size-medium);
  font-weight: 600;
  color: white;
  letter-spacing: -0.3px;
  display: flex;
  align-items: center;
  
  .q-avatar {
    border-radius: 4px;
  }
}

.flex-grow {
  flex: 1;
}

.nav-section {
  margin: 0;
}

.nav-btn {
  border-radius: 8px;
  font-weight: 500;
  color: #e4e9f2;
  font-size: 15px;
  padding: 8px 12px;
  min-height: 36px;
  
  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }
  
  .q-icon {
    font-size: 1.4rem;
  }
  
  &.q-btn--flat {
    min-height: 36px;
    padding: 0 16px;
  }
}

.user-menu-btn {
  border-radius: 8px;
  padding: 4px;
  color: #e4e9f2;
  
  &:hover {
    color: white;
    background: rgba(255, 255, 255, 0.1);
  }
  
  .q-icon {
    font-size: 1.6rem;
  }

  :deep(.q-menu) {
    margin-top: 12px;
  }
}

.modern-menu {
  border-radius: 12px;
  margin-top: 8px;
  background: white;
  width: 280px;
  
  :deep(.q-item) {
    min-height: 40px;
    font-size: 0.9rem;
    color: var(--text-color);
    
    &:hover {
      background: rgba(0, 0, 0, 0.03);
      color: var(--primary-color);
    }
    
    .q-icon {
      font-size: 1.2rem;
      color: #666;
    }
  }

  .q-item.text-center {
    background: #f8fafc;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
  }

  .q-separator {
    background: rgba(0, 0, 0, 0.06);
  }

  .q-radio {
    font-size: 0.9rem;
  }
}

.z-layers {
  .sidebar-container {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    width: var(--app-sidebar-width);
    z-index: 1;
    background: white;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
    
    @media (max-width: 600px) {
      width: 100%;
      height: 50vh;
      bottom: 0;
      top: auto;
    }
  }
  
  .floating-elements {
    position: absolute;
    bottom: 20px;
    left: calc(var(--app-sidebar-width) + 20px);
    right: 20px;
    z-index: 2;
    
    @media (max-width: 600px) {
      left: 20px;
      bottom: 52vh;
    }
  }
}

.map-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;

  &.with-sidebar {
    @media (min-width: 601px) {
      margin-left: var(--app-sidebar-width);
      width: calc(100% - var(--app-sidebar-width));
    }
  }
}

.q-page-container {
  height: calc(100vh - 50px); // Adjust based on your header height
}

.q-page {
  height: 100%;
}

:deep(.q-btn-toggle) {
  .q-btn {
    border: 1px solid currentColor;
  }
}

.feedback-textarea {
  .q-field__native {
    min-height: 120px !important;
  }
  
  textarea {
    line-height: 1.4;
  }
}

.disclaimer {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  border-left: 4px solid var(--primary-color);
  
  .text-subtitle2 {
    color: var(--primary-color);
  }
  
  .text-caption {
    color: #475569;
    line-height: 1.5;
  }
}
</style>