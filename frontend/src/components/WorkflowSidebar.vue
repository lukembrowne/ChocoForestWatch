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
    <q-expansion-item
      v-for="(step, index) in workflowSteps"
      :key="index"
      :icon="step.icon"
      :label="step.label"
      :caption="step.caption"
      :disable="!currentProject || index > completedSteps"
      :default-opened="index === activeStep"
      @update:model-value="(val) => handleStepToggle(index, val)"
    >
      <q-card>
        <q-card-section>
          <component :is="step.component" @step-completed="stepCompleted(index)" />
        </q-card-section>
      </q-card>
    </q-expansion-item>
  </q-list>
</template>

<script>
import { ref, computed, watch } from 'vue'
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
    AOIDefinitionComponent,
    TrainingComponent,
    PredictionComponent,
    // AnalysisComponent
  },
  setup() {
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const completedSteps = ref(-1)
    const activeStep = ref(-1)

    const currentProject = computed(() => projectStore.currentProject)

    const workflowSteps = [
      { label: 'Define AOI', icon: 'map', component: 'AOIDefinitionComponent', caption: 'Set the area of interest' },
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

    const selectProject = async (project) => {
      await projectStore.loadProject(project.id)
      if (project.isNew !== undefined || projectStore.currentProject.aoi === null) {
        completedSteps.value = 0
        activeStep.value = 0 // Automatically open the AOI definition step
        console.log("setting active step to 0")
        console.log(activeStep.value)
        $q.notify({
          message: 'Please define the Area of Interest (AOI) for this project',
          color: 'info',
          icon: 'info'
        })
      } else {
        completedSteps.value = 1
        activeStep.value = 2 // Move to the next step if AOI is already defined
      }
    }

    const stepCompleted = (index) => {
      completedSteps.value = Math.max(completedSteps.value, index)
      activeStep.value = index + 1 // Move to the next step
    }

    const handleStepToggle = (index, isOpened) => {
      if (isOpened) {
        activeStep.value = index
      }
    }

    watch(currentProject, (newProject) => {
      if (newProject && (!newProject.aoi || newProject.isNew)) {
        activeStep.value = 0 // Ensure AOI step is open when project changes
      }
    })

    return {
      currentProject,
      workflowSteps,
      completedSteps,
      activeStep,
      openProjectDialog,
      stepCompleted,
      handleStepToggle
    }
  }
}
</script>