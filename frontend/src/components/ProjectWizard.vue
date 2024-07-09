<template>
  <div class="project-wizard q-pa-md">
    <q-stepper
      v-model="step"
      ref="stepper"
      color="primary"
      animated
      flat
      :contracted="$q.screen.lt.md"
    >
      <q-step
        :name="1"
        title="Project Setup"
        icon="add_circle"
        :done="step > 1"
      />

      <q-step
        :name="2"
        title="Data Preparation"
        icon="map"
        :done="step > 2"
      />

      <q-step
        :name="3"
        title="Model Training"
        icon="school"
        :done="step > 3"
      />

      <q-step
        :name="4"
        title="Prediction"
        icon="insights"
      />
    </q-stepper>

    <div class="content q-mt-md">
      <router-view></router-view>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

export default defineComponent({
  name: 'ProjectWizard',
  setup() {
    const step = ref(1);
    const route = useRoute();

    const stepMap = {
      '/project-setup': 1,
      '/data-preparation': 2,
      '/model-training': 3,
      '/prediction': 4
    };

    watch(() => route.path, (newPath) => {
      step.value = stepMap[newPath] || 1;
    }, { immediate: true });

    return {
      step
    };
  }
});
</script>

<style scoped>
.project-wizard {
  display: flex;
  flex-direction: column;
}

.content {
  flex-grow: 1;
}
</style>