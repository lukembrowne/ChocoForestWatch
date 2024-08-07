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

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered class="bg-grey-1">
      <div class="q-pa-md">
        <component :is="currentSectionComponent" @close="leftDrawerOpen = false" />
      </div>
    </q-drawer>

    <q-page-container>
      <q-page class="relative-position">
        <div id="map" class="map-container"></div>
        <custom-layer-switcher />
        <AOIFloatingCard v-if="showAOICard" />
        <DrawingControlsCard v-if="showDrawingControls" />
        <PolygonListCard v-if="showPolygonList" />
      </q-page>
    </q-page-container>
  </q-layout>
</template>


<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import ProjectSelectionDialog from 'components/ProjectSelectionDialog.vue'
import TrainingComponent from 'components/TrainingSetEditor.vue'
import PredictAnalyzeComponent from 'components/PredictAnalyzeComponent.vue'
import CustomLayerSwitcher from 'components/CustomLayerSwitcher.vue'
import ModelEvaluationDialog from 'components/ModelEvaluationDialog.vue'
import ModelTrainingDialog from 'components/ModelTrainingDialog.vue'
import AOIFloatingCard from 'components/AOIFloatingCard.vue'
import DrawingControlsCard from 'components/DrawingControlsCard.vue'
import PolygonListCard from 'components/PolygonListCard.vue'

export default {
  name: 'MainLayout',
  components: {
    TrainingComponent,
    ModelTrainingDialog,
    PredictAnalyzeComponent,
    CustomLayerSwitcher,
    ModelEvaluationDialog,
    AOIFloatingCard,
    DrawingControlsCard,
    PolygonListCard
  },
  setup() {
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const mapStore = useMapStore()
    const isExpanded = ref(true)
    const leftDrawerOpen = ref(true)
    const currentSection = ref('aoi')
    const currentProject = computed(() => projectStore.currentProject)
    const showAOICard = ref(false)
    const showDrawingControls = ref(false)
    const showPolygonList = ref(false)

    const sections = [
      { name: 'projects', icon: 'folder', component: null, tooltip: 'Select or create a project' },
      { name: 'Training data', icon: 'school', component: TrainingComponent, tooltip: 'Create training data' },
      { name: 'Fit model', icon: 'model_training', component: null, tooltip: 'Train a new model' },
      { name: 'Model evaluation', icon: 'assessment', component: null, tooltip: 'Evaluate trained models' },
      { name: 'Predict & Analyze', icon: 'analytics', component: null, tooltip: 'Predict and analyze land cover' }
    ]

    const handleSectionClick = (section) => {
      if (section.name === 'Model evaluation') {
        openModelEvaluationDialog()
      } else if (section.name === 'projects') {
        openProjectDialog()
      } else if (section.name === 'Fit model') {
        openModelTrainingDialog()
      } else if (section.name === 'Predict & Analyze') {
        openPredictAnalyzeDialog()
      } else {
        leftDrawerOpen.value = true
        currentSection.value = section.name
      }

      if (section.name === 'Training data') {
        showDrawingControls.value = true
        showPolygonList.value = true
      } else {
        showDrawingControls.value = false
        showPolygonList.value = false
      }
    }

    const sidebarWidth = computed(() => isExpanded.value ? 300 : 60)
    const currentSectionComponent = computed(() =>
      sections.find(s => s.name === currentSection.value)?.component
    )

    onMounted(() => {

      // // Standard loading sequence
      // // Initialize map
      // mapStore.initMap('map')

      // // // Open project dialogue to have user select or create new project
      // openProjectDialog()


      // Load default project and map date to make things easier
      console.log('Loading default project...')
      mapStore.initMap('map')
      currentSection.value = 'training'
      // Sleep 2 seconds
      setTimeout(() => {
        projectStore.loadProject(29)
      }, 1000)

      setTimeout(() => {
        mapStore.updateBasemap('2022-08')
      }, 1000)

    })

    const openProjectDialog = () => {
      $q.dialog({
        component: ProjectSelectionDialog
      }).onOk((project) => {
        selectProject(project)
      })
    }



    const openModelTrainingDialog = () => {
      $q.dialog({
        component: ModelTrainingDialog
      }).onOk((response) => {
        // Handle the response from model training
        console.log('Model training completed:', response)
        $q.notify({
          color: 'positive',
          message: 'Model training initiated successfully',
          icon: 'check'
        })

        openModelEvaluationDialog()
      })
    }

    const openModelEvaluationDialog = async () => {
      $q.dialog({
        component: ModelEvaluationDialog
      })
    }

    const openPredictAnalyzeDialog = () => {
      $q.dialog({
        component: PredictAnalyzeComponent,
        // You can pass props here if needed
        // props: {
        //   someProp: someValue
        // }
      }).onOk((result) => {
        // Handle any result if needed
        console.log('Predict and Analyze completed:', result)
      })
    }

    const selectProject = async (project) => {
      // Clear existing AOIs
      mapStore.clearAOI()

      await projectStore.loadProject(project.id)


      if (project.isNew !== undefined || !projectStore.currentProject.aoi) {
        showAOICard.value = true
        currentSection.value = null
      } else {
        showAOICard.value = false
        toggleSection('Training data')
        $q.notify({
          message: 'Project loaded successfully',
          color: 'positive',
          icon: 'check'
        })
      }
    }

    watch(() => projectStore.currentProject?.aoi, (newAOI) => {
      if (newAOI) {
        showAOICard.value = false
        currentSection.value = 'Training data'
      }
    })

    return {
      isExpanded,
      currentSection,
      sections,
      sidebarWidth,
      currentSectionComponent,
      currentProject,
      openProjectDialog,
      openModelTrainingDialog,
      leftDrawerOpen,
      showAOICard,
      showDrawingControls,
      showPolygonList,
      openModelEvaluationDialog,
      handleSectionClick,
      openPredictAnalyzeDialog
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