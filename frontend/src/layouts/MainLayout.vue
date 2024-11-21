<template>
  <q-layout view="hHh LpR fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>Choco Forest Watch</q-toolbar-title>
        
        <div class="row items-center no-wrap">
          <q-btn v-for="section in sections" :key="section.name" flat square :icon="section.icon" :label="section.name"
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

    <q-page-container>
      <q-page class="relative-position">
        <div id="map" class="map-container" v-if="!showHotspotVerification"></div>
        <custom-layer-switcher v-if="!showHotspotVerification" />
        <AOIFloatingCard v-if="showAOICard" v-on:aoiSaved="handleAOISaved" />
        <TrainingAndPolygonManager v-if="showTrainingAndPolygonManager" />
        <LandCoverAnalysis v-if="showLandCoverAnalysis" />
        <DeforestationAnalysis v-if="showDeforestationAnalysis" />
        <HotspotVerification v-if="showHotspotVerification" />
        <!-- Dont show map date slider when AOI is being created -->
        <BasemapDateSlider v-if="!showAOICard & !showHotspotVerification"/>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import ProjectSelectionDialog from 'components/projects/ProjectSelectionDialog.vue'
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
    HotspotVerification
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

    onMounted(() => {

      // Standard loading sequence
      // Initialize map
      mapStore.initMap('map')
      mapStore.initializeBasemapDates()

      // // Open project dialogue to have user select or create new project
      openProjectDialog()


      // // Load default project and map date to make things easier
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
        openProjectDialog()
      } else {
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

    const openProjectDialog = () => {
      $q.dialog({
        component: ProjectSelectionDialog
      }).onOk((project) => {
        selectProject(project)
      })
    }

    // Remove the openModelTrainingDialog function from here

    const selectProject = async (project) => {
      // Clear existing AOIs
      mapStore.clearAOI()

      console.log("Loading project")
      await projectStore.loadProject(project.id)

      if (project.isNew !== undefined || !projectStore.currentProject.aoi) {
        showAOICard.value = true
        currentSection.value = null
      } else {

        // Clear AOI
        showAOICard.value = false

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
      openProjectDialog,
      showAOICard,
      showTrainingAndPolygonManager,
      handleSectionClick,
      handleAOISaved,
      showLandCoverAnalysis,
      showDeforestationAnalysis,
      showHotspotVerification,
      currentUser,
      handleUserSettings,
      handleLogout
    }
  }
}
</script>

<style scoped>
.map-container {
  position: absolute;
  top: 0;
  /* Adjust based on your header height */
  left: 0px;
  /* Width of the drawer */
  right: 0;
  bottom: 0;
}

/* Adjust when drawer is closed */
.q-layout--prevent-focus .map-container {
  left: 0;
}

.q-toolbar .q-btn {
  margin-left: 8px;
}

/* Ensure the page container allows for absolute positioning */
.q-page-container {
  position: relative;
}

.q-btn-dropdown {
  .q-list {
    min-width: 200px;
  }
}

/* Add smooth transitions for hover effects */
.q-item {
  transition: background-color 0.3s ease;

  &:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }
}

/* Make the avatar and username look better */
.q-avatar {
  font-size: 32px;
  font-weight: bold;
}

.text-subtitle1 {
  font-weight: 500;
}
</style>