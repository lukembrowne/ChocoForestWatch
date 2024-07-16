<template>
  <q-page class="row">
    <q-drawer v-model="leftDrawerOpen" show-if-above :width="300" :breakpoint="400" bordered class="bg-grey-3">
      <q-scroll-area class="fit">
        <q-list padding>
          <q-item-label header>Create New Project</q-item-label>
          <q-item>
            <q-item-section>
              <q-input v-model="newProject.name" label="Project Name" dense />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-input v-model="newProject.description" label="Description" type="textarea" dense />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-btn label="Create Project" color="primary" @click="createProject" :disable="!aoiDrawn"
                class="full-width" />
            </q-item-section>
          </q-item>
          <q-item v-if="!aoiDrawn">
            <q-item-section>
              <q-badge color="warning">
                Please draw an AOI on the map before creating the project
              </q-badge>
            </q-item-section>
          </q-item>

          <q-separator spaced />


          <div class="map-controls">
            <q-btn label="Draw AOI" color="primary" @click="startDrawingAOI" :disable="isDrawing" />
            <q-btn label="Clear AOI" color="negative" @click="clearAOI" :disable="!aoiDrawn" class="q-ml-sm" />
          </div>

          <q-separator spaced />

          <q-item-label header>Saved Projects</q-item-label>
          <q-item v-for="project in projects" :key="project.id" clickable v-ripple @click="selectProject(project.id)">
            <q-item-section>
              <q-item-label>{{ project.name }}</q-item-label>
              <q-item-label caption>{{ project.description }}</q-item-label>
            </q-item-section>
          </q-item>

          <q-item v-if="projects.length === 0">
            <q-item-section>
              <q-item-label caption>No saved projects</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <div class="col">
      <div class="map-container" style="height: calc(100vh - 50px);">
        <BaseMapComponent ref="baseMap" @map-ready="onMapReady" class="full-height full-width" />
      </div>
    </div>


  </q-page>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useProjectStore } from 'stores/projectStore';
import { useQuasar } from 'quasar';
import BaseMapComponent from 'components/BaseMapComponent.vue';
import Draw, {
  createBox,
} from 'ol/interaction/Draw.js'; import VectorSource from 'ol/source/Vector';
import VectorLayer from 'ol/layer/Vector';
import GeoJSON from 'ol/format/GeoJSON';


export default {
  name: 'HomePage',
  components: {
    BaseMapComponent
  },
  setup() {
    const router = useRouter();
    const projectStore = useProjectStore();
    const showCreateProjectDialog = ref(false);
    const newProject = ref({ name: '', description: '' });
    const projects = ref([]);
    const baseMap = ref(null);
    const aoiDrawn = ref(false);
    const drawInteraction = ref(null);
    const vectorLayer = ref(null);
    const isDrawing = ref(false);
    const leftDrawerOpen = ref(true);
    const $q = useQuasar();



    onMounted(async () => {
      await fetchProjects();
    });

    const fetchProjects = async () => {
      try {
        await projectStore.fetchProjects();
        projects.value = projectStore.projects;
      } catch (error) {
        console.error('Error fetching projects:', error);
        // Handle error (show notification, etc.)
      }
    };

    const createProject = async () => {
      if (!aoiDrawn.value) {
        $q.notify({
          color: 'warning',
          message: 'Please draw an Area of Interest before creating the project',
          icon: 'warning'
        });
        return;
      }

      try {
        const aoiFeature = vectorLayer.value.getSource().getFeatures()[0];
        const aoiGeojson = new GeoJSON().writeFeatureObject(aoiFeature, {
          dataProjection: 'EPSG:4326',
          featureProjection: 'EPSG:3857'
        });

        const createdProject = await projectStore.createProject({
          ...newProject.value,
          aoi: aoiGeojson
        });

        showCreateProjectDialog.value = false;
        clearAOI();
        newProject.value = { name: '', description: '' };
        await fetchProjects();

        router.push({ name: 'training' });
      } catch (error) {
        console.error('Error creating project:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to create project: ' + error.message,
          icon: 'error'
        });
      }
    };

    const loadProject = async (projectId) => {
      try {
        await projectStore.loadProject(projectId);
        router.push({ name: 'training'});
      } catch (error) {
        console.error('Error loading project:', error);
        // Handle error (show notification, etc.)
      }
    };

    const selectProject = async (projectId) => {
      try {
        await projectStore.loadProject(projectId);
        router.push({ name: 'training' });
      } catch (error) {
        console.error('Error loading project:', error);
        $q.notify({
          color: 'negative',
          message: 'Failed to load project',
          icon: 'error'
        });
      }
    };


    const onMapReady = (map) => {
      const source = new VectorSource();
      vectorLayer.value = new VectorLayer({
        source: source,
        style: {
          'fill-color': 'rgba(255, 255, 255, 0.2)',
          'stroke-color': '#ffcc33',
          'stroke-width': 2
        }
      });
      map.addLayer(vectorLayer.value);
    };

    const startDrawingAOI = () => {
      if (!baseMap.value || !baseMap.value.map) return;

      isDrawing.value = true;
      const source = vectorLayer.value.getSource();
      source.clear();  // Clear previous drawings

      drawInteraction.value = new Draw({
        source: source,
        type: 'Circle',
        geometryFunction: createBox()
      });

      drawInteraction.value.on('drawend', (event) => {
        const feature = event.feature;
        aoiDrawn.value = true;
        isDrawing.value = false;
        baseMap.value.map.removeInteraction(drawInteraction.value);
      });

      baseMap.value.map.addInteraction(drawInteraction.value);
    };

    const clearAOI = () => {
      if (vectorLayer.value) {
        vectorLayer.value.getSource().clear();
        aoiDrawn.value = false;
      }
    };


    return {
      baseMap,
      aoiDrawn,
      onMapReady,
      startDrawingAOI,
      showCreateProjectDialog,
      newProject,
      projects,
      createProject,
      loadProject,
      clearAOI,
      isDrawing,
      leftDrawerOpen,
      selectProject
    };
  }
};
</script>

<style lang="scss" scoped>
.fullscreen-map {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.map-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.map-overlay {
  position: absolute;
  z-index: 1;
  padding: 10px;
}

.top-left {
  top: 10px;
  left: 10px;
}

.bottom-right {
  bottom: 10px;
  right: 10px;
}
</style>