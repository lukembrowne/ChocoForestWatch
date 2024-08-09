<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="width: 50vw; max-width: 90vw;">
      <q-card-section class="text-center q-pb-none">
        <div class="text-h5 q-mb-md">Welcome to Choco Forest Watch</div>
        <p class="text-body1">
          Monitor and analyze forest cover changes using satellite imagery and machine learning.
        </p>
      </q-card-section>

      <q-card-section>
        <div class="text-h6">Load Existing Project</div>
        <q-table :rows="projects" :columns="columns" row-key="id" :pagination="{ rowsPerPage: 5 }"
          @row-click="onRowClick">
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn flat round color="primary" icon="launch" @click.stop="onOk(props.row)">
                <q-tooltip>Load Project</q-tooltip>
              </q-btn>
              <q-btn flat round color="secondary" icon="edit" @click.stop="openRenameDialog(props.row)">
                <q-tooltip>Rename Project</q-tooltip>
              </q-btn>
              <q-btn flat round color="negative" icon="delete" @click.stop="confirmDelete(props.row)">
                <q-tooltip>Delete Project</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
      </q-card-section>

      <q-separator />

      <q-card-section>
        <div class="text-h6">Create New Project</div>
        <q-form @submit.prevent="validateAndCreateProject">
          <q-input dense rounded outlined v-model="newProject.name" label="Project Name" class="q-mb-md" />
          <q-input dense rounded outlined v-model="newProject.description" label="Description" type="textarea"
            class="q-mb-md" />

          <div class="text-subtitle2 q-mb-sm">Define Land Cover Classes</div>
          <div v-for="(classItem, index) in newProject.classes" :key="index" class="row q-mb-sm">
            <q-input dense rounded outlined v-model="classItem.name" label="Class Name" class="col-6"
              :rules="[val => !!val || 'Name is required']" />
            <q-color v-model="classItem.color" class="col-4 q-ml-md" default-view="palette" :palette="[
              '#019A9D', '#D9B801', '#E8045A', '#B2028A',
              '#2A0449', '#019A9D']" />
            <q-btn flat round color="negative" icon="remove" @click="removeClass(index)" class="col-1 q-ml-sm" />
          </div>
          <q-btn densed rounded outlined label="Add Class" icon="add" color="positive" @click="addClass"
            class="q-mb-md" />

          <q-btn label="Create Project" type="submit" color="primary" class="q-mt-md full-width" rounded />
        </q-form>
      </q-card-section>


      <q-dialog v-model="showRenameDialog">
        <q-card style="min-width: 350px">
          <q-card-section>
            <div class="text-h6">Rename Project</div>
          </q-card-section>

          <q-card-section class="q-pt-none">
            <q-input v-model="newProjectName" label="New Project Name" autofocus @keyup.enter="renameProject" />
          </q-card-section>

          <q-card-actions align="right" class="text-primary">
            <q-btn flat label="Cancel" v-close-popup />
            <q-btn flat label="Rename" @click="renameProject" v-close-popup />
          </q-card-actions>
        </q-card>
      </q-dialog>



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
import { date } from 'quasar'


export default {
  name: 'ProjectSelectionDialog',
  emits: [...useDialogPluginComponent.emits],

  setup() {
    const { dialogRef, onDialogHide, onDialogOK, onDialogCancel } = useDialogPluginComponent()
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const projects = ref([])
    const newProjectName = ref('')
    const projectToRename = ref(null)
    const showRenameDialog = ref(false)
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

    const columns = [
      { name: 'name', required: true, label: 'Name', align: 'left', field: 'name', sortable: true },
      { name: 'description', align: 'left', label: 'Description', field: 'description', sortable: true },
      {
        name: 'updated_at', align: 'left', label: 'Last Updated', field: 'updated_at', sortable: true,
        format: (val) => date.formatDate(val, 'YYYY-MM-DD HH:mm')
      },
      { name: 'actions', align: 'center', label: 'Actions' }
    ]

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

    const validateAndCreateProject = () => {
      console.log("Validating and creating project...")
      if (!newProject.value.name.trim()) {
        $q.dialog({
          title: 'Error',
          message: 'Project name is required. Please enter a name for your project.',
          color: 'negative',
          ok: 'Ok'
        })
        return
      }
      createProject()
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

    const onRowClick = (evt, row) => {
      onDialogOK(row)
    }

    const openRenameDialog = (project) => {
      projectToRename.value = project
      newProjectName.value = project.name
      showRenameDialog.value = true
    }

    const renameProject = async () => {
      if (!newProjectName.value.trim()) {
        $q.notify({
          color: 'negative',
          message: 'Project name cannot be empty',
          icon: 'error'
        })
        return
      }

      try {
        await projectStore.updateProject(projectToRename.value.id, { ...projectToRename.value, name: newProjectName.value })
        await fetchProjects()
        $q.notify({
          color: 'positive',
          message: 'Project renamed successfully',
          icon: 'check'
        })
      } catch (error) {
        console.error('Error renaming project:', error)
        $q.notify({
          color: 'negative',
          message: 'Failed to rename project',
          icon: 'error'
        })
      }
    }

    const confirmDelete = (project) => {
      $q.dialog({
        title: 'Confirm Delete',
        message: `Are you sure you want to delete the project "${project.name}"?`,
        cancel: true,
        persistent: true
      }).onOk(async () => {
        try {
          await projectStore.deleteProject(project.id)
          await fetchProjects()
          $q.notify({
            color: 'positive',
            message: 'Project deleted successfully',
            icon: 'check'
          })
        } catch (error) {
          console.error('Error deleting project:', error)
          $q.notify({
            color: 'negative',
            message: 'Failed to delete project',
            icon: 'error'
          })
        }
      })
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
      removeClass,
      columns,
      onRowClick,
      validateAndCreateProject,
      newProjectName,
      projectToRename,
      showRenameDialog,
      renameProject,
      confirmDelete,
      openRenameDialog
    }
  }
}
</script>