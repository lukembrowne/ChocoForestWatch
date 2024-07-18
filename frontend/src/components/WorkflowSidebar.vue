<template>
  <q-list padding>
    <q-item-label header>Project</q-item-label>
    <q-item clickable v-ripple @click="openProjectDialog">
      <q-item-section avatar>
        <q-icon name="folder" />
      </q-item-section>
      <q-item-section>
        {{ currentProject ? currentProject.name : 'Select Project' }}
      </q-item-section>
    </q-item>

    <q-separator spaced />

    <q-item-label header>Workflow</q-item-label>
    <q-expansion-item v-for="(step, index) in workflowSteps" :key="index" :icon="step.icon" :label="step.label"
      :caption="step.caption" :disable="!currentProject || index > completedSteps">
      <q-card>
        <q-card-section>
          <component :is="step.component" @step-completed="stepCompleted(index)" />
        </q-card-section>
      </q-card>
    </q-expansion-item>
  </q-list>
</template>

<script>
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'
import ProjectSelectionDialog from 'components/ProjectSelectionDialog.vue'
import AOIDefinitionComponent from 'components/AOIDefinition.vue'
import TrainingComponent from 'components/Training.vue'
import PredictionComponent from 'components/Prediction.vue'
// import AnalysisComponent from 'components/Analysis.vue'

export default {
  name: 'WorkflowSidebar',
  components: {
    ProjectSelectionDialog,
    AOIDefinitionComponent,
    TrainingComponent,
    PredictionComponent,
    // AnalysisComponent
  },
  setup() {
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const projectDialogOpen = ref(false)
    const completedSteps = ref(-1)

    const currentProject = computed(() => projectStore.currentProject)

    const workflowSteps = [
      { label: 'Define AOI', icon: 'map', component: 'AOIDefinition', caption: 'Set the area of interest' },
      { label: 'Training', icon: 'school', component: 'TrainingComponent', caption: 'Create training data' },
      { label: 'Prediction', icon: 'insights', component: 'PredictionComponent', caption: 'Run land cover prediction' },
      { label: 'Analysis', icon: 'analytics', component: 'AnalysisComponent', caption: 'Analyze changes' }
    ]

    const openProjectDialog = () => {
      $q.dialog({
        component: ProjectSelectionDialog
      }).onOk((project) => {
        selectProject(project)
      })
    }

    const selectProject = (project) => {
      projectStore.setCurrentProject(project)
      completedSteps.value = -1 // Reset completed steps when a new project is selected
    }

    const stepCompleted = (index) => {
      completedSteps.value = Math.max(completedSteps.value, index)
    }

    return {
      currentProject,
      workflowSteps,
      projectDialogOpen,
      completedSteps,
      openProjectDialog,
      selectProject,
      stepCompleted
    }
  }
}
</script>