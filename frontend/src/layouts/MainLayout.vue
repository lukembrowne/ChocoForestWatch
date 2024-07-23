<template>
  <q-layout view="hHh Lpr lFf" class="full-height">

    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>Choco Forest Watch</q-toolbar-title>
        <q-tabs>
          <q-route-tab to="/" label="Home" icon="home" />
          <q-route-tab to="/debug" label="Debug" icon="insert_chart" />

        </q-tabs>
      </q-toolbar>
    </q-header>
    <q-page-container class="full-height">
      <div class="full-height full-width relative-position">
         <!-- Map container -->
         <div id="map" class="absolute-full" style="min-height: 100vh; min-width: 100vw;">
          <div class="absolute-center">Map should render here</div>
        </div>

        <!-- Floating sidebar -->
        <div class="floating-sidebar absolute-left full-height bg-white" :style="{ width: sidebarWidth + 'px' }">
          <!-- Icon sidebar -->
          <div class="icon-sidebar bg-primary text-white full-height" style="width: 60px; z-index: 1000;">
            <q-list>
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
            <div v-if="isExpanded" class="expanded-content bg-white full-height"
              style="width: 240px; margin-left: 60px; z-index: 999;">
              <component :is="currentSectionComponent" @close="isExpanded = false" />
            </div>
          </q-slide-transition>
        </div>
      </div>

      <div class="debug-info absolute-bottom-right q-pa-md bg-white">
        Sidebar width: {{ sidebarWidth }}px<br>
        Is Expanded: {{ isExpanded }}<br>
        Current Section: {{ currentSection }}
      </div>
    </q-page-container>
  </q-layout>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import TrainingSection from 'components/Training.vue'
import AnalysisSection from 'components/Analysis.vue'
import { useMapStore } from 'src/stores/mapStore'

export default {
  name: 'MainLayout',
  components: {
    TrainingSection,
    AnalysisSection
  },
  setup() {
    const mapStore = useMapStore()
    const isExpanded = ref(true)
    const currentSection = ref(null)

    const sections = [
      { name: 'training', icon: 'school', component: TrainingSection },
      { name: 'analysis', icon: 'analytics', component: AnalysisSection }
    ]

    const toggleSection = (sectionName) => {
      if (currentSection.value === sectionName && isExpanded.value) {
        isExpanded.value = false
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
      mapStore.initMap('map')
    })

    return {
      isExpanded,
      currentSection,
      sections,
      toggleSection,
      sidebarWidth,
      currentSectionComponent
    }
  }
}
</script>

<style scoped>
.full-height {
  height: 100vh;
}

.floating-sidebar {
  display: flex;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1000;
  background-color: white;
}

.icon-sidebar {
  position: absolute;
  top: 0;
  left: 0;
  background-color: white;
}

.expanded-content {
  position: absolute;
  top: 0;
  left: 60px;
  box-shadow: 2px 0 5px rgba(0, 0, 0, 0.1);
  background-color: white;
}
</style>