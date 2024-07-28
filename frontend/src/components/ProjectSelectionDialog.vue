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
          
          <div class="text-subtitle2 q-mt-md q-mb-sm">Define Land Cover Classes</div>
          <div v-for="(classItem, index) in newProject.classes" :key="index" class="row q-mb-sm">
            <q-input v-model="classItem.name" label="Class Name" class="col-6" :rules="[val => !!val || 'Name is required']" />
            <q-color v-model="classItem.color" class="col-4 q-ml-md" />
            <q-btn flat round color="negative" icon="remove" @click="removeClass(index)" class="col-1 q-ml-sm" />
          </div>
          <q-btn label="Add Class" color="positive" @click="addClass" class="q-mb-md" />

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
    const newProject = ref({
      name: '',
      description: '',
      classes: [
        { name: 'Forest', color: '#00FF00' },
        { name: 'Non-Forest', color: '#FFFF00' },
        { name: 'Cloud', color: '#FFFFFF' },
        { name: 'Shadow', color: '#808080' },
        { name: 'Water', color: '#0000FF' }
      ]
    })

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
      if (newProject.value.classes.length < 2) {
        $q.notify({
          color: 'negative',
          message: 'At least 2 classes are required',
          icon: 'error'
        })
        return
      }

      if (new Set(newProject.value.classes.map(c => c.name)).size !== newProject.value.classes.length) {
        $q.notify({
          color: 'negative',
          message: 'Class names must be unique',
          icon: 'error'
        })
        return
      }

      try {
        console.log("Creating project...")
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

    const addClass = () => {
      newProject.value.classes.push({ name: '', color: '#000000' })
    }

    const removeClass = (index) => {
      newProject.value.classes.splice(index, 1)
    }

    return {
      dialogRef,
      onDialogHide,
      onOk: onDialogOK,
      onCancel: onDialogCancel,
      projects,
      newProject,
      createProject,
      addClass,
      removeClass
    }
  }
}
</script>