<template>
  <q-layout view="hHh LpR fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar class="q-px-md">
        <q-toolbar-title class="gt-xs">Choco Forest Watch</q-toolbar-title>
        <q-toolbar-title class="lt-sm">CFW</q-toolbar-title>
        
        <div class="row items-center no-wrap">
          <q-btn v-for="section in sections" :key="section.name" flat square :icon="section.icon" :label="$q.screen.gt.xs ? section.name : ''"
            class="q-px-sm"
            @click="handleSectionClick(section)">
            <q-tooltip>{{ section.tooltip }}</q-tooltip>
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

            <q-item clickable v-ripple @click="handleUserSettings">
              <q-item-section avatar>
                <q-icon name="settings" />
              </q-item-section>
              <q-item-section>Settings</q-item-section>
            </q-item>

            <q-item clickable v-ripple @click="handleLogout">
              <q-item-section avatar>
                <q-icon name="logout" />
              </q-item-section>
              <q-item-section>Logout</q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
      </q-toolbar>
    </q-header>

    <q-page-container class="q-pa-none">
      <q-page class="relative-position">
        <div class="z-layers">
          <div id="map" class="map-container" :class="{ 'with-sidebar': showAnyPanel }"></div>
          <div class="sidebar-container" v-if="showAnyPanel">
            <ProjectSelection v-if="showProjectSelection" />
            <TrainingAndPolygonManager v-if="showTrainingAndPolygonManager" />
            <LandCoverAnalysis v-if="showLandCoverAnalysis" />
            <DeforestationAnalysis v-if="showDeforestationAnalysis" />
            <HotspotVerification v-if="showHotspotVerification" />
          </div>
          <AOIFloatingCard v-if="showAOICard" @aoiSaved="handleAOISaved" />
          <div class="floating-elements">
            <BasemapDateSlider v-if="!showAOICard && !showHotspotVerification" class="date-slider" />
          </div>
          <custom-layer-switcher v-if="!showHotspotVerification" />
        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import ProjectSelection from 'components/projects/ProjectSelectionDialog.vue'
import TrainingAndPolygonManager from 'components/training/TrainingAndPolygonManager.vue'
import CustomLayerSwitcher from 'components/CustomLayerSwitcher.vue'
import AOIFloatingCard from 'components/projects/AOIFloatingCard.vue'
import BasemapDateSlider from 'components/BasemapDateSlider.vue'
import LandCoverAnalysis from 'components/analysis/LandCoverAnalysis.vue'
import DeforestationAnalysis from 'components/analysis/DeforestationAnalysis.vue'
import HotspotVerification from 'components/analysis/HotspotVerification.vue'
import { useRouter } from 'vue-router'
import authService from '../services/auth'


export default {
  name: 'MainLayout',
  components: {
    TrainingAndPolygonManager,
    CustomLayerSwitcher,
    AOIFloatingCard,
    BasemapDateSlider,
    LandCoverAnalysis,
    DeforestationAnalysis,
    HotspotVerification,
    ProjectSelection
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
    const sections = [
      { name: 'projects', icon: 'folder', component: null, tooltip: 'Select or create a project' },
      { name: 'Train Model', icon: 'school', component: TrainingAndPolygonManager, tooltip: 'Train Model' },
      { name: 'Land Cover', icon: 'analytics', component: LandCoverAnalysis, tooltip: 'Predict and analyze land cover' },
      { name: 'Deforestation', icon: 'forest', component: DeforestationAnalysis, tooltip: 'Analyze deforestation' },
      { name: 'Verify Hotspots', icon: 'fact_check', component: HotspotVerification, tooltip: 'Verify deforestation hotspots' }
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
      showLandCoverAnalysis.value || 
      showDeforestationAnalysis.value || 
      showHotspotVerification.value
    )

    onMounted(() => {

      // Standard loading sequence
      // Initialize map
      mapStore.initMap('map')
      mapStore.initializeBasemapDates()
      showProjectSelection.value = true

      // // Open project dialogue to have user select or create new project
      // console.log('Loading default project...')
      // mapStore.initMap('map')
      // currentSection.value = 'training'
      // // Sleep 2 seconds
      // setTimeout(() => {
      //   projectStore.loadProject(36)
      // }, 2000)

      // mapStore.initializeBasemapDates()

      // setTimeout(() => {
      //   mapStore.updateBasemap('2022-01')
      // }, 1000)

    })

    const handleSectionClick = async (section) => {
      // if (currentSection.value === 'Train Model') {
      //   await promptSaveChanges();
      // }
      
      console.log("Clicked section: ", section)
      if (section.name === 'projects') {
        showProjectSelection.value = true
        showTrainingAndPolygonManager.value = false
        showLandCoverAnalysis.value = false
        showDeforestationAnalysis.value = false
        showHotspotVerification.value = false
      } else {
        showProjectSelection.value = false
        currentSection.value = section.name
      }

      if (section.name === 'Train Model') {
        showTrainingAndPolygonManager.value = true
      } else {
        showTrainingAndPolygonManager.value = false
      }

      if (section.name === 'Land Cover') {
        showLandCoverAnalysis.value = true
      } else {
        showLandCoverAnalysis.value = false
      }

      if (section.name === 'Deforestation') {
        showDeforestationAnalysis.value = true
      } else {
        showDeforestationAnalysis.value = false
      }

      if (section.name === 'Verify Hotspots') {
        showHotspotVerification.value = true
      } else {
        showHotspotVerification.value = false
      }
    }

    const selectProject = async (project) => {
      // Clear existing AOIs
      mapStore.clearAOI()

      console.log("Loading project")
      await projectStore.loadProject(project.id)

      if (project.isNew !== undefined || !projectStore.currentProject.aoi) {
        // Hide project selection when showing AOI card
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

    // NOT WORKING - not receving the emits
    const handleAOISaved = (eventData) => {
      console.log('AOI saved event received in MainLayout', eventData)
      showAOICard.value = false
      handleSectionClick({ name: 'Train Model' })
      $q.notify({
        message: 'AOI saved successfully. Entering training mode.',
        color: 'positive',
        icon: 'check'
      })
    }

    watch(() => projectStore.currentProject?.aoi, (newAOI) => {
      if (newAOI) {
        showAOICard.value = false
        currentSection.value = 'Train Model'
      }
    })

    const handleUserSettings = () => {
      $q.notify({
        message: 'User settings coming soon!',
        color: 'info',
        icon: 'settings'
      })
    }

    const handleLogout = () => {
      $q.dialog({
        title: 'Confirm Logout',
        message: 'Are you sure you want to logout?',
        cancel: true,
        persistent: true
      }).onOk(() => {
        authService.logout()
        router.push('/login')
        $q.notify({
          message: 'Successfully logged out',
          color: 'positive',
          icon: 'logout'
        })
      })
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
      handleUserSettings,
      handleLogout,
      showProjectSelection,
      selectProject,
      showAnyPanel
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
</style>