<template>
  <div class="projects-container">
    <h2>My Projects</h2>
    
    <!-- Create New Project Form -->
    <div class="create-project" v-if="showCreateForm">
      <h3>Create New Project</h3>
      <form @submit.prevent="createProject">
        <div class="form-group">
          <label>Project Name:</label>
          <input v-model="newProject.name" type="text" required />
        </div>
        <div class="form-group">
          <label>Description:</label>
          <textarea v-model="newProject.description"></textarea>
        </div>
        <button type="submit">Create Project</button>
        <button type="button" @click="showCreateForm = false">Cancel</button>
      </form>
    </div>

    <!-- New Project Button -->
    <button v-else @click="showCreateForm = true">New Project</button>

    <!-- Projects List -->
    <div class="projects-list">
      <div v-if="loading">Loading projects...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else-if="projects.length === 0">No projects found. Create one to get started!</div>
      <div v-else class="project-cards">
        <div v-for="project in projects" :key="project.id" class="project-card">
          <h3>{{ project.name }}</h3>
          <p>{{ project.description }}</p>
          <p>Created: {{ new Date(project.created_at).toLocaleDateString() }}</p>
          <div class="project-actions">
            <button @click="viewProject(project)">View</button>
            <button @click="deleteProject(project)" class="delete">Delete</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api';

export default {
  name: 'ProjectsList',
  data() {
    return {
      projects: [],
      loading: true,
      error: null,
      showCreateForm: false,
      newProject: {
        name: '',
        description: ''
      }
    };
  },
  async created() {
    await this.loadProjects();
  },
  methods: {
    async loadProjects() {
      try {
        this.loading = true;
        const response = await api.getProjects();
        this.projects = response.data;
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to load projects';
      } finally {
        this.loading = false;
      }
    },
    async createProject() {
      try {
        await api.createProject(this.newProject);
        this.showCreateForm = false;
        this.newProject = { name: '', description: '' };
        await this.loadProjects();
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to create project';
      }
    },
    async deleteProject(project) {
      if (confirm(`Are you sure you want to delete ${project.name}?`)) {
        try {
          await api.deleteProject(project.id);
          await this.loadProjects();
        } catch (error) {
          this.error = error.response?.data?.error || 'Failed to delete project';
        }
      }
    },
    viewProject(project) {
      // Navigate to project detail view (you'll need to set up this route)
      this.$router.push(`/projects/${project.id}`);
    }
  }
};
</script>

<style scoped>
.projects-container {
  padding: 20px;
}

.create-project {
  margin: 20px 0;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.project-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.project-card {
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 15px;
}

.project-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  background-color: #4CAF50;
  color: white;
}

button.delete {
  background-color: #f44336;
}

button:hover {
  opacity: 0.9;
}

.error {
  color: red;
  margin: 10px 0;
}
</style> 