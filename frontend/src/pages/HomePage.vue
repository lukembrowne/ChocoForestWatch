<template>
  <q-page class="flex flex-center">
    <div class="text-center">
      <h1 class="text-h3 q-mb-md">Welcome to Choco Forest Watch</h1>
      <p class="text-h6 q-mb-lg">Train XGBoost models for land cover classification</p>
      <q-btn color="primary" label="Start New Project" @click="startNewProject" class="q-mr-sm" />
      <q-btn color="secondary" label="Manage Projects" to="/projects" />
    </div>
  </q-page>
</template>

<script>
import { defineComponent } from 'vue';
import { useRouter } from 'vue-router';

export default defineComponent({
  name: 'HomePage',
  setup() {
    const router = useRouter();

    const startNewProject = () => {
      router.push('/project-setup');
    };

    return {
      startNewProject
    };
  }
});
</script>