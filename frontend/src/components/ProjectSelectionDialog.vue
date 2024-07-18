<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide">
      <q-card class="q-dialog-plugin" style="width: 500px; max-width: 80vw;">
        <q-card-section>
          <div class="text-h6">Select or Create Project</div>
        </q-card-section>
  
        <q-card-section>
          <q-list bordered separator>
            <q-item v-for="project in projects" :key="project.id" clickable v-ripple @click="selectProject(project)">
              <q-item-section>
                <q-item-label>{{ project.name }}</q-item-label>
                <q-item-label caption>{{ project.description }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
  
          <q-separator spaced />
  
          <div class="text-h6 q-mb-md">Create New Project</div>
          <q-form @submit="createProject">
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
  import { useDialogPluginComponent } from 'quasar'
  import { useProjectStore } from 'src/stores/projectStore'
  
  export default {
    name: 'ProjectSelectionDialog',
    emits: [...useDialogPluginComponent.emits],
  
    setup () {
      const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent()
      const projectStore = useProjectStore()
      const projects = ref([])
      const newProject = ref({ name: '', description: '' })
  
      onMounted(async () => {
        console.log("Mounted ProjectSelectionDialogue")
        await fetchProjects()
      })
  
      const fetchProjects = async () => {
        try {
          await projectStore.fetchProjects()
          projects.value = projectStore.projects
        } catch (error) {
          console.error('Error fetching projects:', error)
          // You might want to show an error message to the user here
        }
      }
  
      const selectProject = (project) => {
        onDialogOK(project)
      }
  
      const createProject = async () => {
        try {
          const createdProject = await projectStore.createProject(newProject.value)
          onDialogOK(createdProject)
        } catch (error) {
          console.error('Error creating project:', error)
          // You might want to show an error message to the user here
        }
      }
  
      return {
        dialogRef,
        onDialogHide,
        projects,
        newProject,
        selectProject,
        createProject
      }
    }
  }
  </script>
  