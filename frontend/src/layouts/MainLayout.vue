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
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page class="relative-position">
        <div id="map" class="map-container"></div>
        <custom-layer-switcher />
        <AOIFloatingCard v-if="showAOICard" v-on:aoiSaved="handleAOISaved" />
        <TrainingAndPolygonManager v-if="showTrainingAndPolygonManager" />
        <PredictAnalyzeManager v-if="showPredictAnalyzeManager" />
        <BasemapDateSlider />
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
import PredictAnalyzeManager from 'components/analysis/PredictAnalyzeManager.vue'
import CustomLayerSwitcher from 'components/CustomLayerSwitcher.vue'
import AOIFloatingCard from 'components/projects/AOIFloatingCard.vue'
import BasemapDateSlider from 'components/BasemapDateSlider.vue'


export default {
  name: 'MainLayout',
  components: {
    TrainingAndPolygonManager,
    PredictAnalyzeManager,
    CustomLayerSwitcher,
    AOIFloatingCard,
    BasemapDateSlider
  },
  setup() {
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const mapStore = useMapStore()
    const currentSection = ref('aoi')
    const currentProject = computed(() => projectStore.currentProject)
    const showAOICard = ref(false)
    const showTrainingAndPolygonManager = ref(false)
    const showPredictAnalyzeManager = ref(false)
    const sections = [
      { name: 'projects', icon: 'folder', component: null, tooltip: 'Select or create a project' },
      { name: 'Train Model', icon: 'school', component: TrainingAndPolygonManager, tooltip: 'Train Model' },
      { name: 'Predict & Analyze', icon: 'analytics', component: PredictAnalyzeManager, tooltip: 'Predict and analyze land cover' }
    ]

    const sidebarWidth = computed(() => isExpanded.value ? 300 : 60)
    const currentSectionComponent = computed(() =>
      sections.find(s => s.name === currentSection.value)?.component
    )

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

      if (section.name === 'Predict & Analyze') {
        showPredictAnalyzeManager.value = true
      } else {
        showPredictAnalyzeManager.value = false
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
      showPredictAnalyzeManager,
      handleAOISaved
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
</style>