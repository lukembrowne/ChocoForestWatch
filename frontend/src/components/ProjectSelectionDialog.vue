<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="min-width: 350px">
      <q-card-section>
        <div class="text-h6">Select or Create Project</div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-list bordered separator>
          <q-item v-for="project in projects" :key="project.id" clickable v-ripple @click="onOk(project)">
            <q-item-section>
              <q-item-label>{{ project.name }}</q-item-label>
              <q-item-label caption>{{ project.description }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <q-separator spaced />

        <div class="text-subtitle2 q-mb-sm">Create New Project</div>
        <q-form @submit.prevent="createProject">
          <q-input v-model="newProject.name" label="Project Name" :rules="[val => !!val || 'Name is required']" />
          <q-input v-model="newProject.description" label="Description" type="textarea" />
          <q-btn label="Create Project" type="submit" color="primary" class="q-mt-md" />
        </q-form>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Cancel" color="primary" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useDialogPluginComponent, useQuasar } from 'quasar'
import { useProjectStore } from 'src/stores/projectStore'

export default {
  name: 'ProjectSelectionDialog',
  emits: [...useDialogPluginComponent.emits],

  setup () {
    const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent()
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const projects = ref([])
    const newProject = ref({ name: '', description: '' })

    onMounted(async () => {
      await fetchProjects()
    })

    const fetchProjects = async () => {
      try {
        projects.value = await projectStore.fetchProjects()
      } catch (error) {
        console.error('Error fetching projects:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to fetch projects',
          icon: 'error'
        })
      }
    }

    const createProject = async () => {
      try {
        const createdProject = await projectStore.createProject(newProject.value)
        onDialogOK({ ...createdProject, isNew: true })
      } catch (error) {
        console.error('Error creating project:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to create project',
          icon: 'error'
        })
      }
    }

    return {
      dialogRef,
      onDialogHide,
      onOk: onDialogOK,
      onCancel: onDialogCancel,
      projects,
      newProject,
      createProject
    }
  }
}
</script>