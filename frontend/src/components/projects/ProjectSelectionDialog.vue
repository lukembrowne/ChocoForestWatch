<template>
  <div class="project-selection-container">
    <q-card class="project-card">
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">{{ t('projects.existingProjects') }}</div>
        <q-table 
          :rows="projects" 
          :columns="columns" 
          row-key="id" 
          :pagination="{ rowsPerPage: 5 }"
          @row-click="onRowClick"
          dense
          flat
        >
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn flat round color="primary" icon="launch" @click.stop="onOk(props.row)">
                <q-tooltip>{{ t('projects.tooltips.load') }}</q-tooltip>
              </q-btn>
              <q-btn flat round color="secondary" icon="edit" @click.stop="openRenameDialog(props.row)">
                <q-tooltip>{{ t('projects.tooltips.rename') }}</q-tooltip>
              </q-btn>
              <q-btn flat round color="negative" icon="delete" @click.stop="confirmDelete(props.row)">
                <q-tooltip>{{ t('projects.tooltips.delete') }}</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
      </q-card-section>

      <q-separator />

      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">{{ t('projects.createNew') }}</div>
        <q-form @submit.prevent="validateAndCreateProject">
          <q-input 
            dense 
            rounded 
            outlined 
            v-model="newProject.name" 
            :label="t('projects.projectName')"
            class="q-mb-md" 
          />
          <q-input 
            dense 
            rounded 
            outlined 
            v-model="newProject.description" 
            :label="t('projects.description')"
            type="textarea"
            class="q-mb-md" 
          />
          <q-btn 
            :label="t('projects.createButton')"
            type="submit" 
            color="primary" 
            class="q-mt-md full-width" 
            rounded 
          />
        </q-form>
      </q-card-section>
    </q-card>

    <!-- Rename Dialog -->
    <q-dialog v-model="showRenameDialog">
      <q-card style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">{{ t('projects.rename.title') }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-input 
            v-model="newProjectName" 
            :label="t('projects.rename.newName')"
            autofocus 
            @keyup.enter="renameProject" 
          />
        </q-card-section>

        <q-card-actions align="right" class="text-primary">
          <q-btn flat :label="t('projects.buttons.cancel')" v-close-popup />
          <q-btn flat :label="t('projects.buttons.rename')" @click="renameProject" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useProjectStore } from 'src/stores/projectStore'
import { date } from 'quasar'

export default {
  name: 'ProjectSelection',
  emits: ['project-selected'],

  setup(props, { emit }) {
    const $q = useQuasar()
    const projectStore = useProjectStore()
    const { t } = useI18n()
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
      { 
        name: 'name', 
        required: true, 
        label: t('projects.table.name'),
        align: 'left', 
        field: 'name', 
        sortable: true 
      },
      { 
        name: 'updated_at', 
        align: 'left', 
        label: t('projects.table.updated'),
        field: 'updated_at', 
        sortable: true,
        format: (val) => date.formatDate(val, 'MM/DD/YY'),
        style: 'width: 100px'
      },
      { 
        name: 'actions', 
        align: 'right', 
        label: t('projects.table.actions'),
        style: 'width: 120px'
      }
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
          message: t('projects.notifications.fetchFailed'),
          icon: 'error'
        })
      }
    }

    const validateAndCreateProject = () => {
      console.log("Validating and creating project...")
      if (!newProject.value.name.trim()) {
        $q.dialog({
          title: t('common.error'),
          message: t('projects.nameRequired'),
          color: 'negative',
          ok: t('common.ok')
        })
        return
      }
      createProject()
    }

    const createProject = async () => {
      if (newProject.value.classes.length < 2) {
        $q.notify({
          color: 'negative',
          message: t('projects.minClasses'),
          icon: 'error'
        })
        return
      }

      if (new Set(newProject.value.classes.map(c => c.name)).size !== newProject.value.classes.length) {
        $q.notify({
          color: 'negative',
          message: t('projects.uniqueClasses'),
          icon: 'error'
        })
        return
      }

      try {
        console.log("Creating project...")
        const createdProject = await projectStore.createProject(newProject.value)
        
        emit('project-selected', { ...createdProject, isNew: true })
        
        newProject.value = {
          name: '',
          description: '',
          classes: [
            { name: 'Forest', color: '#00FF00' },
            { name: 'Non-Forest', color: '#FFFF00' },
            { name: 'Cloud', color: '#FFFFFF' },
            { name: 'Shadow', color: '#808080' },
            { name: 'Water', color: '#0000FF' }
          ]
        }

        $q.notify({
          message: t('projects.created'),
          color: 'positive',
          icon: 'check'
        })
      } catch (error) {
        console.error('Error creating project:', error)
        $q.notify({
          color: 'negative',
          message: t('projects.failedCreate'),
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
      onOk(row)
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
          message: t('projects.rename.empty'),
          icon: 'error'
        })
        return
      }

      try {
        await projectStore.updateProject(projectToRename.value.id, { ...projectToRename.value, name: newProjectName.value })
        await fetchProjects()
        $q.notify({
          color: 'positive',
          message: t('projects.rename.success'),
          icon: 'check'
        })
      } catch (error) {
        console.error('Error renaming project:', error)
        $q.notify({
          color: 'negative',
          message: t('projects.rename.failed'),
          icon: 'error'
        })
      }
    }

    const confirmDelete = (project) => {
      $q.dialog({
        title: t('projects.delete.title'),
        message: t('projects.delete.confirm', { name: project.name }),
        cancel: true,
        persistent: true
      }).onOk(async () => {
        try {
          await projectStore.deleteProject(project.id)
          await fetchProjects()
          $q.notify({
            color: 'positive',
            message: t('projects.delete.success'),
            icon: 'check'
          })
        } catch (error) {
          console.error('Error deleting project:', error)
          $q.notify({
            color: 'negative',
            message: t('projects.delete.failed'),
            icon: 'error'
          })
        }
      })
    }

    const onOk = (project) => {
      emit('project-selected', project)
    }

    return {
      projects,
      newProject,
      onOk,
      columns,
      onRowClick,
      validateAndCreateProject,
      newProjectName,
      projectToRename,
      showRenameDialog,
      renameProject,
      confirmDelete,
      openRenameDialog,
      t
    }
  }
}
</script>

<style lang="scss" scoped>
.project-selection-container {
  height: calc(100vh - var(--app-header-height));
  overflow-y: auto;
}

.project-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: auto;
  border-radius: 0;
  box-shadow: none;
}

.q-table {
  background-color: transparent;
}

.project-item {
  border-radius: 8px;
  margin: 4px;
  background-color: #f5f5f5;
  transition: background-color 0.3s;

  &:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }
}

.q-form {
  .q-input {
    margin-bottom: 8px;
  }
}
</style>