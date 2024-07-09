<template>
    <div class="project-management">
      <h2>Project Management</h2>
      
      <!-- Create New Project Form -->
      <q-form @submit="createProject" class="q-gutter-md">
        <q-input v-model="newProject.name" label="Project Name" required />
        <q-input v-model="newProject.description" label="Description" type="textarea" />
        <q-btn label="Create Project" type="submit" color="primary" />
      </q-form>
  
      <!-- List of Existing Projects -->
      <q-list bordered class="q-mt-md">
        <q-item v-for="project in projects" :key="project.id" clickable v-ripple @click="loadProject(project)">
          <q-item-section>
            <q-item-label>{{ project.name }}</q-item-label>
            <q-item-label caption>{{ project.description }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn flat round color="negative" icon="delete" @click.stop="deleteProject(project.id)" />
          </q-item-section>
        </q-item>
      </q-list>
    </div>
  </template>
  
  <script>
  import { ref, onMounted } from 'vue';
  import { useQuasar } from 'quasar';
  import apiService from 'src/services/api';
  
  export default {
    name: 'ProjectManagement',
    setup() {
      const $q = useQuasar();
      const projects = ref([]);
      const newProject = ref({ name: '', description: '' });
  
      const fetchProjects = async () => {
        try {
          const response = await apiService.getProjects();
          projects.value = response.data;
        } catch (error) {
          console.error('Error fetching projects:', error);
          $q.notify({ type: 'negative', message: 'Failed to fetch projects' });
        }
      };
  
      const createProject = async () => {
        try {
          await apiService.createProject(newProject.value);
          $q.notify({ type: 'positive', message: 'Project created successfully' });
          newProject.value = { name: '', description: '' };
          await fetchProjects();
        } catch (error) {
          console.error('Error creating project:', error);
          $q.notify({ type: 'negative', message: 'Failed to create project' });
        }
      };
  
      const loadProject = (project) => {
        // Implement logic to load project data into the application state
        console.log('Loading project:', project);
        // You might want to use Vuex or Pinia for state management here
      };
  
      const deleteProject = async (id) => {
        try {
          await apiService.deleteProject(id);
          $q.notify({ type: 'positive', message: 'Project deleted successfully' });
          await fetchProjects();
        } catch (error) {
          console.error('Error deleting project:', error);
          $q.notify({ type: 'negative', message: 'Failed to delete project' });
        }
      };
  
      onMounted(fetchProjects);
  
      return {
        projects,
        newProject,
        createProject,
        loadProject,
        deleteProject
      };
    }
  };
  </script>