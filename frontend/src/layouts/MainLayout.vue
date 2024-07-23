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
      <div class="row no-wrap full-height">
        <!-- Sidebar column -->
        <div class="sidebar-column" :style="{ width: sidebarWidth + 'px' }">
          <!-- Icon sidebar -->
          <div class="icon-sidebar bg-white text-primary full-height" style="width: 60px;">
            <q-list>
              <q-item v-for="section in sections" :key="section.name" 
                      clickable @click="toggleSection(section.name)"
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
import { ref, computed, onMounted, nextTick } from 'vue'
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
    const isExpanded = ref(false)
    const currentSection = ref(null)

    const sections = [
      { name: 'training', icon: 'school', component: TrainingSection },
      { name: 'analysis', icon: 'analytics', component: AnalysisSection }
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
      nextTick(() => {
        mapStore.initMap('map')
      })
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
  border-right: 1px solid #e0e0e0;
}
.expanded-content {
  position: absolute;
  top: 0;
  left: 60px;
  width: 240px;
  z-index: 1;
  box-shadow: 2px 0 5px rgba(0,0,0,0.1);
}
.map-column {
  position: relative;
}
#map {
  width: 100%;
}
</style>