<template>
  <q-layout view="hHh Lpr lFf" class="full-height">

    <q-header elevated bordered class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>Choco Forest Watch</q-toolbar-title>
        <q-tabs>
          <q-route-tab to="/" label="Home" icon="home" />
          <q-route-tab to="/debug" label="Debug" icon="insert_chart" />

        </q-tabs>
      </q-toolbar>
    </q-header>

    <q-page-container class="full-height">
      <div class="row no-wrap full-height">
        <!-- Sidebar column -->
        <div class="sidebar-column" :style="{ width: sidebarWidth + 'px' }">
          <!-- Icon sidebar -->
          <div class="icon-sidebar bg-white text-primary full-height" style="width: 60px;">
            <q-list>
              <q-item clickable @click="openProjectDialog"><q-item-section avatar>
                  <q-icon name="folder" />
                </q-item-section></q-item>
              <q-item v-for="section in sections" :key="section.name" clickable @click="toggleSection(section.name)"
                :active="currentSection === section.name">
                <q-item-section avatar>
                  <q-icon :name="section.icon" />
                </q-item-section>
              </q-item>
            </q-list>
          </div>

          <!-- Expanded section content -->
          <q-slide-transition>
            <div v-if="isExpanded" class="expanded-content bg-white full-height">
              <component :is="currentSectionComponent" @close="isExpanded = false" />
            </div>
          </q-slide-transition>
        </div>

        <!-- Map column -->
        <div class="col map-column">
          <div id="map" class="absolute-full" style="min-height: 100vh; min-width: 100vw;">
          </div>
        </div>
      </div>
    </q-page-container>
  </q-layout>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import { useMapStore } from 'src/stores/mapStore'
import ProjectSelectionDialog from 'components/ProjectSelectionDialog.vue'
import AOIDefinitionComponent from 'components/AOIDefinition.vue'
import TrainingComponent from 'components/Training.vue'
import AnalysisComponent from 'components/Analysis.vue'

export default {
  name: 'MainLayout',
  components: {
    AOIDefinitionComponent,
    TrainingComponent,
    AnalysisComponent
  },
  setup() {
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const mapStore = useMapStore()
    const isExpanded = ref(true)
    const currentSection = ref('aoi')
    const currentProject = computed(() => projectStore.currentProject)


    const sections = [
      { name: 'aoi', icon: 'map', component: AOIDefinitionComponent },
      { name: 'training', icon: 'school', component: TrainingComponent },
      { name: 'analysis', icon: 'analytics', component: AnalysisComponent }
    ]

    const toggleSection = (sectionName) => {
      if (currentSection.value === sectionName && isExpanded.value) {
        isExpanded.value = false
        currentSection.value = null
      } else {
        isExpanded.value = true
        currentSection.value = sectionName
      }
    }

    const sidebarWidth = computed(() => isExpanded.value ? 300 : 60)
    const currentSectionComponent = computed(() =>
      sections.find(s => s.name === currentSection.value)?.component
    )

    onMounted(() => {

      // Initialize map
      mapStore.initMap('map')

      // Open project dialogue to have user select or create new project
      openProjectDialog()

      //  // Load default project and map date to make things easier
      //  console.log('Loading default project...')
      // mapStore.initMap('map')
      // // Sleep 2 seconds
      // projectStore.loadProject(9)
      // setTimeout(() => {
      //   mapStore.updateBasemap('2022-08')
      // }, 1000)

    })

    const openProjectDialog = () => {
      $q.dialog({
        component: ProjectSelectionDialog
      }).onOk((project) => {
        selectProject(project)
      })
    }

    const selectProject = async (project) => {
      await projectStore.loadProject(project.id)
      if (project.isNew !== undefined || projectStore.currentProject.aoi === null) {
        $q.notify({
          message: 'Please define the Area of Interest (AOI) for this project',
          color: 'info',
          icon: 'info'
        })
      } else {

        // If project has aoi
        currentSection.value = 'training'

        $q.notify({
          message: 'Project loaded successfully',
          color: 'positive',
          icon: 'check'
        })
      }
    }

    return {
      isExpanded,
      currentSection,
      sections,
      toggleSection,
      sidebarWidth,
      currentSectionComponent,
      currentProject,
      openProjectDialog,
    }
  }
}
</script>

<style scoped>
.full-height {
  height: 100vh;
}

.sidebar-column {
  display: flex;
  position: relative;
  transition: width 0.3s ease;
}

.icon-sidebar {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 2;
}

.expanded-content {
  position: absolute;
  top: 0;
  left: 60px;
  width: 240px;
  z-index: 1;
  box-shadow: 2px 0 50px rgba(0, 0, 0, 0.1);
}

.map-column {
  position: relative;
}

#map {
  width: 100%;
}
</style>