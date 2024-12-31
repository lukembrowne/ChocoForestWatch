<template>
  <q-layout view="hHh LpR fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar class="q-px-md">
        <q-toolbar-title class="gt-xs">{{ t('header.title') }}</q-toolbar-title>
        <q-toolbar-title class="lt-sm">{{ t('header.titleShort') }}</q-toolbar-title>
        
        <div class="row items-center no-wrap">
          <q-btn v-for="section in sections" :key="section.name" flat square :icon="section.icon" 
            :label="$q.screen.gt.xs ? t(`navigation.${section.id}.name`) : ''"
            class="q-px-sm"
            @click="handleSectionClick(section)">
            <q-tooltip>{{ t(`navigation.${section.id}.tooltip`) }}</q-tooltip>
          </q-btn>
        </div>

        <q-btn-dropdown flat round icon="account_circle" class="q-ml-md" v-if="currentUser">
          <q-list>
            <q-item class="text-center q-py-md">
              <q-item-section>
                <q-avatar size="72px" color="primary" text-color="white">
                  {{ currentUser.username.charAt(0).toUpperCase() }}
                </q-avatar>
                <div class="text-subtitle1 q-mt-md">{{ currentUser.username }}</div>
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
          <div id="map" class="map-container" :class="{ 'with-sidebar': showAnyPanel || showAOICard }" v-if="!showUnifiedAnalysis"></div>
          <div class="sidebar-container" v-if="(showAnyPanel || showAOICard) && !showUnifiedAnalysis">
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
          <div class="floating-elements">
            <BasemapDateSlider v-if="!showAOICard && !showUnifiedAnalysis" class="date-slider" />
          </div>
          <custom-layer-switcher v-if="!showUnifiedAnalysis" mapId="training" />
        </div>
      </q-page>
    </q-page-container>

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


export default {
  name: 'MainLayout',
  components: {
    TrainingAndPolygonManager,
    CustomLayerSwitcher,
    AOIFloatingCard,
    BasemapDateSlider,
    ProjectSelection,
    UnifiedAnalysis
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
    const sections = [
      { id: 'projects', name: 'projects', icon: 'folder', component: null },
      { id: 'training', name: 'Train Model', icon: 'school', component: TrainingAndPolygonManager },
      { id: 'analysis', name: 'Analysis', icon: 'analytics', component: UnifiedAnalysis }
    ]

    const sidebarWidth = computed(() => isExpanded.value ? 300 : 60)
    const currentSectionComponent = computed(() =>
      sections.find(s => s.name === currentSection.value)?.component
    )

    const router = useRouter()
    const currentUser = computed(() => authService.getCurrentUser())

    const showAnyPanel = computed(() => 
      showProjectSelection.value || 
      showTrainingAndPolygonManager.value || 
      showUnifiedAnalysis.value || 
      showLandCoverAnalysis.value || 
      showDeforestationAnalysis.value || 
      showHotspotVerification.value
    )

    const { t, locale } = useI18n()
    const currentLocale = ref('en')

    const route = useRoute();
    const welcomeStore = useWelcomeStore();

    const showHelp = () => {
      const currentPath = route.path;
      if (currentPath.startsWith('/projects')) {
        welcomeStore.showHelp('projects');
      } else if (currentPath.startsWith('/training')) {
        welcomeStore.showHelp('training');
      } else if (currentPath.startsWith('/analysis')) {
        welcomeStore.showHelp('analysis');
      }
    };

    onMounted(async () => {
      try {
        // Load user settings first
        const { data } = await api.getUserSettings()
        if (data.preferred_language) {
          currentLocale.value = data.preferred_language
          locale.value = data.preferred_language
        }
      } catch (error) {
        console.error('Error loading user settings:', error)
      }

      // Standard loading sequence
      // Initialize map
      mapStore.initMap('map')
      mapStore.initializeBasemapDates()
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

      if (section.name === 'projects') {
        showProjectSelection.value = true;
      } else if (section.name === 'Train Model') {
        showTrainingAndPolygonManager.value = true;
      } else if (section.name === 'Analysis') {
        showUnifiedAnalysis.value = true;
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
    }
  }
}
</script>

<style lang="scss">
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
</style>