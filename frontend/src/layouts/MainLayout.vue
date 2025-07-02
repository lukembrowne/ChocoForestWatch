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
          <!-- Admin navigation buttons -->
          <template v-if="isAdmin">
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
          </template>

          <!-- Feedback button always visible -->
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

        <!-- User / guest menu -->
        <q-btn-dropdown 
          flat 
          class="user-menu-btn q-ml-lg" 
          size="md"
          dropdown-icon="arrow_drop_down"
          content-class="user-dropdown-content"
        >
          <template #label>
            <div class="user-menu-label">
              <q-avatar 
                v-if="currentUser" 
                size="24px" 
                class="user-avatar"
                :class="{ 'admin-avatar': isAdmin }"
              >
                <span class="avatar-text">{{ currentUser?.user?.username?.charAt(0)?.toUpperCase() || '?' }}</span>
                <q-badge 
                  v-if="isAdmin" 
                  color="amber" 
                  floating 
                  rounded 
                  class="admin-badge"
                >
                  <q-icon name="admin_panel_settings" size="10px" />
                </q-badge>
              </q-avatar>
              <q-icon v-else name="person_outline" size="24px" />
            </div>
          </template>

          <q-list class="user-menu-list">
            <!-- User Profile Section -->
            <div v-if="currentUser" class="user-profile-section">
              <q-item class="user-profile-item">
                <q-item-section avatar>
                  <q-avatar size="42px" class="profile-avatar" :class="{ 'admin-avatar': isAdmin }">
                    <span class="avatar-text">{{ currentUser?.user?.username?.charAt(0)?.toUpperCase() || '?' }}</span>
                    <q-badge 
                      v-if="isAdmin" 
                      color="amber" 
                      floating 
                      rounded 
                      class="admin-badge"
                    >
                      <q-icon name="admin_panel_settings" size="10px" />
                    </q-badge>
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label class="username">{{ currentUser?.user?.username || 'Unknown User' }}</q-item-label>
                  <q-item-label caption class="user-role">
                    {{ isAdmin ? 'Administrator' : 'User' }}
                  </q-item-label>
                </q-item-section>
              </q-item>
              <q-separator class="profile-separator" />
            </div>

            <!-- Language Selection -->
            <q-item class="language-section">
              <q-item-section avatar>
                <q-icon name="language" class="section-icon" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="section-label">{{ t('common.language') || 'Language' }}</q-item-label>
                <div class="language-buttons">
                  <q-btn
                    :class="['language-btn', { 'active': currentLocale === 'en' }]"
                    flat
                    no-caps
                    @click="handleLocaleChange('en')"
                  >
                     English
                  </q-btn>
                  <q-btn
                    :class="['language-btn', { 'active': currentLocale === 'es' }]"
                    flat
                    no-caps
                    @click="handleLocaleChange('es')"
                  >
                     Español
                  </q-btn>
                </div>
              </q-item-section>
            </q-item>

            <q-separator />

            <!-- Menu Actions -->
            <q-item clickable v-ripple @click="showHelp" class="menu-action-item">
              <q-item-section avatar>
                <q-icon name="help_outline" class="action-icon" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ t('common.showHelp') }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item clickable v-ripple @click="welcomeStore.openAboutModal()" class="menu-action-item">
              <q-item-section avatar>
                <q-icon name="info_outline" class="action-icon" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ t('common.about') }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-separator v-if="currentUser" />

            <!-- Auth Actions -->
            <q-item v-if="currentUser" clickable v-ripple @click="handleLogout" class="menu-action-item logout-item">
              <q-item-section avatar>
                <q-icon name="logout" class="action-icon logout-icon" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ t('common.logout') }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item v-else clickable v-ripple @click="showLoginModal = true" class="menu-action-item login-item">
              <q-item-section avatar>
                <q-icon name="login" class="action-icon login-icon" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ t('common.login') }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
      </q-toolbar>
    </q-header>

    <q-page-container class="q-pa-none">
      <q-page class="relative-position">
        <div class="z-layers">
          <div id="map" class="map-container" :class="{ 'with-sidebar': showSidebar }" v-if="!showUnifiedAnalysis && !showAdminDashboard"></div>
          <div class="sidebar-container" v-if="showSidebar && !showUnifiedAnalysis && !showAdminDashboard">
            <ProjectSelection 
              v-if="isAdmin && showProjectSelection" 
              @project-selected="selectProject"
            />
            <AOIFloatingCard 
              v-if="isAdmin && showAOICard" 
              @aoi-saved="handleAOISaved"
            />
            <TrainingAndPolygonManager v-if="isAdmin && showTrainingAndPolygonManager" />
            <SidebarPanel v-if="!isAdmin" />
          </div>
          <UnifiedAnalysis v-if="isAdmin && showUnifiedAnalysis" />
          <SystemDashboard v-if="isAdmin && showAdminDashboard" />
          <div class="floating-elements" v-if="!showAOICard && !showUnifiedAnalysis && !showAdminDashboard">
            <BasemapDateSlider class="date-slider" />
          </div>
          <MapLegend v-if="!showUnifiedAnalysis && !showAdminDashboard" />
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

    <!-- Welcome Modal for first-time users and help button -->
    <WelcomeAboutModal mode="welcome" />
    
    <!-- About Modal -->
    <WelcomeAboutModal mode="about" />

    <!-- Login Modal -->
    <LoginModal 
      v-model="showLoginModal" 
      @login-success="handleLoginSuccess"
      @register-success="handleRegisterSuccess"
    />

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
import SidebarPanel from 'components/sidebar/SidebarPanel.vue'
import BasemapDateSlider from 'components/BasemapDateSlider.vue'
import MapLegend from 'components/MapLegend.vue'
import UnifiedAnalysis from 'components/analysis/UnifiedAnalysis.vue'
import { useRouter, useRoute } from 'vue-router'
import authService from '../services/auth'
import { useAuthStore } from '../stores/authStore'
import api from '../services/api'
import { GeoJSON } from 'ol/format'
import { useI18n } from 'vue-i18n'
import { useWelcomeStore } from 'src/stores/welcomeStore'
import SystemDashboard from 'src/components/admin/SystemDashboard.vue'
import WelcomeAboutModal from 'src/components/welcome/WelcomeAboutModal.vue'
import LoginModal from 'src/components/auth/LoginModal.vue'



export default {
  name: 'MainLayout',
  components: {
    TrainingAndPolygonManager,
    CustomLayerSwitcher,
    AOIFloatingCard,
    SidebarPanel,
    BasemapDateSlider,
    MapLegend,
    ProjectSelection,
    UnifiedAnalysis,
    SystemDashboard,
    WelcomeAboutModal,
    LoginModal
  },
  setup() {
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const mapStore = useMapStore()
    const authStore = useAuthStore()
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
    const isAdmin = computed(() => currentUser.value?.user?.is_superuser === true)

    const sections = computed(() => {
      if (!isAdmin.value) {
        return [] // public visitors see no nav sections
      }

      const adminSections = [
        { id: 'projects', name: 'projects', icon: 'folder', component: null },
        { id: 'training', name: 'Train Model', icon: 'school', component: TrainingAndPolygonManager },
        { id: 'analysis', name: 'Analysis', icon: 'analytics', component: UnifiedAnalysis }
      ]

      // Superuser-only dashboard
      adminSections.push({
        id: 'admin',
        name: 'Admin Dashboard',
        icon: 'dashboard',
        component: SystemDashboard
      })

      return adminSections
    })

    const sidebarWidth = computed(() => isExpanded.value ? 300 : 60)
    const currentSectionComponent = computed(() =>
      sections.value.find(s => s.name === currentSection.value)?.component
    )

    const router = useRouter()
    // Initialize auth store on component mount
    authStore.initializeAuth()
    const currentUser = computed(() => authStore.currentUser)

    const showAnyPanel = computed(() => 
      showProjectSelection.value || 
      showTrainingAndPolygonManager.value || 
      showUnifiedAnalysis.value || 
      showLandCoverAnalysis.value || 
      showDeforestationAnalysis.value || 
      showHotspotVerification.value ||
      showAdminDashboard.value
    )

    const showSidebar = computed(() => {
      return isAdmin.value ? (showAnyPanel.value || showAOICard.value) : true
    })

    const { t, locale } = useI18n()
    const currentLocale = ref('en')

    const route = useRoute();
    const welcomeStore = useWelcomeStore();

    const showHelp = () => {
      // Open the main welcome modal for all users
      welcomeStore.showWelcomeModal = true;
    };


    onMounted(async () => {
      console.log("Mounted MainLayout")
      
      // Create and append Umami script
      const script = document.createElement('script')
      script.async = true
      script.src = `${import.meta.env.VITE_UMAMI_URL}/script.js`
      script.setAttribute('data-website-id', import.meta.env.VITE_UMAMI_WEBSITE_ID)
      script.onload = () => console.log('✅ Umami script loaded successfully')
      script.onerror = (error) => console.error('❌ Umami script failed to load:', error)
      document.head.appendChild(script)
      console.log('📝 Umami script tag added to DOM')
      try {
        // Load language preference from localStorage
        const savedLocale = localStorage.getItem('preferred_language')
        if (savedLocale && ['en', 'es'].includes(savedLocale)) {
          currentLocale.value = savedLocale
          locale.value = savedLocale
        }
      } catch (error) {
        console.error('Error in mounted:', error)
      }

      // Check if we should show welcome modal for public users
      welcomeStore.checkWelcomeModalStatus()

      // Standard loading sequence
      console.log("Initializing map")
      mapStore.initMap('map', true)
      mapStore.initializeBasemapDates()

      const isAdmin = currentUser.value?.user?.is_superuser === true

      if (isAdmin) {
        // legacy workflow for admins
        showProjectSelection.value = true
      } else {
        try {
          // Load default project automatically
          await projectStore.loadDefaultProject()

          // Show planet & prediction basemaps for a representative date (Jan-2022 for now)
          mapStore.updateBasemap('2022-01', 'planet')

            // Auto-load CFW Composite 2022 forest cover map
            mapStore.addBenchmarkLayer('northern_choco_test_2025_06_20_2022_merged_composite')
        } catch (err) {
          console.error('Failed to load default project:', err)
          $q.notify({
            message: 'Failed to load default project',
            icon: 'error',
            color: 'negative'
          })
        }
      }
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
        mapStore.updateBasemap('2022-01', 'planet')
        mapStore.updateBasemap('2022-01', 'predictions')

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
          mapStore.updateBasemap(initialDate, 'planet'),
          mapStore.updateBasemap(initialDate, 'predictions'),
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
        authStore.logout()
        $q.notify({
          message: t('common.logoutSuccess'),
          color: 'positive',
          icon: 'logout'
        })
      })
    }

    const handleLocaleChange = async (newLocale) => {
      try {
        // Save language preference to localStorage
        localStorage.setItem('preferred_language', newLocale)
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
    const showLoginModal = ref(false)


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
          user_id: currentUser.value?.user?.id,
          user_name: currentUser.value?.user?.username,
          user_email: currentUser.value?.user?.email,
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

      const handleLoginSuccess = (user) => {
      console.log('Login successful for user:', user)
      // Auth store is already updated by the login modal
    }

    const handleRegisterSuccess = (user) => {
      console.log('Registration successful for user:', user)
      // Auth store will be updated by the login that happens after registration
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
      showSidebar,
      showUnifiedAnalysis,
      showHelp,
      showFeedbackDialog,
      feedbackType,
      feedbackMessage,
      submittingFeedback,
      feedbackOptions,
      submitFeedback,
      testSentryError,
      showAdminDashboard,
      router,
      isAdmin,
      welcomeStore,
      showLoginModal,
      handleLoginSuccess,
      handleRegisterSuccess
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
  padding: 6px 8px;
  color: #e4e9f2;
  transition: all 0.2s ease;
  
  &:hover {
    color: white;
    background: rgba(255, 255, 255, 0.1);
    transform: scale(1.05);
  }
  
  .user-menu-label {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .user-avatar {
    background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
    box-shadow: 0 2px 8px rgba(25, 118, 210, 0.3);
    
    &.admin-avatar {
      background: linear-gradient(135deg, #f57c00 0%, #e65100 100%);
      box-shadow: 0 2px 8px rgba(245, 124, 0, 0.3);
    }
    
    .avatar-text {
      font-weight: 600;
      font-size: 12px;
    }
  }
  
  .admin-badge {
    .q-icon {
      color: #333;
      font-size: 10px;
    }
  }
}

// Enhanced dropdown content styles
:deep(.user-dropdown-content) {
  margin-top: 8px;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12), 0 2px 16px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.user-menu-list {
  background: white;
  width: 300px;
  padding: 0;
  
  // User Profile Section
  .user-profile-section {
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    
    .user-profile-item {
      padding: 16px;
      
      .profile-avatar {
        background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
        box-shadow: 0 2px 8px rgba(25, 118, 210, 0.3);
        
        &.admin-avatar {
          background: linear-gradient(135deg, #f57c00 0%, #e65100 100%);
          box-shadow: 0 2px 8px rgba(245, 124, 0, 0.3);
        }
        
        .avatar-text {
          font-weight: 600;
          font-size: 16px;
        }
      }
      
      .username {
        font-weight: 600;
        font-size: 16px;
        color: #1e293b;
        margin-bottom: 2px;
      }
      
      .user-role {
        font-size: 12px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500;
      }
    }
    
    .profile-separator {
      background: rgba(148, 163, 184, 0.2);
      margin: 0;
    }
  }
  
  // Language Section
  .language-section {
    padding: 12px 16px;
    
    .section-icon {
      color: #64748b;
      font-size: 20px;
    }
    
    .section-label {
      font-weight: 500;
      color: #374151;
      margin-bottom: 8px;
      font-size: 13px;
    }
    
    .language-buttons {
      display: flex;
      gap: 6px;
      margin-top: 8px;
      
      .language-btn {
        flex: 1;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 12px;
        font-weight: 500;
        color: #64748b;
        background: rgba(248, 250, 252, 0.5);
        border: 1px solid rgba(226, 232, 240, 0.8);
        transition: all 0.2s ease;
        
        &:hover {
          background: rgba(239, 246, 255, 0.8);
          border-color: #3b82f6;
          color: #3b82f6;
          transform: translateY(-1px);
        }
        
        &.active {
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          color: white;
          border-color: #3b82f6;
          box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
        }
      }
    }
  }
  
  // Menu Action Items
  .menu-action-item {
    padding: 12px 16px;
    transition: all 0.2s ease;
    
    &:hover {
      background: rgba(59, 130, 246, 0.04);
      
      .action-icon {
        color: #3b82f6;
        transform: scale(1.1);
      }
      
      .q-item__label {
        color: #1e293b;
      }
    }
    
    .action-icon {
      color: #64748b;
      font-size: 20px;
      transition: all 0.2s ease;
    }
    
    .q-item__label {
      font-weight: 500;
      color: #374151;
      font-size: 14px;
    }
    
    &.logout-item:hover {
      background: rgba(239, 68, 68, 0.04);
      
      .logout-icon {
        color: #ef4444;
      }
    }
    
    &.login-item:hover {
      background: rgba(34, 197, 94, 0.04);
      
      .login-icon {
        color: #22c55e;
      }
    }
  }
  
  // Separators
  .q-separator {
    background: rgba(148, 163, 184, 0.15);
    margin: 0;
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