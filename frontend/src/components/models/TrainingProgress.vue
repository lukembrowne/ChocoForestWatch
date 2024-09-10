<template>
  <q-dialog v-model="dialogModel" persistent>
    <q-card style="min-width: 300px">
      <q-card-section class="row items-center">
        <div class="text-h6">Training and Prediction in Progress</div>
        <q-space />
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-linear-progress
          :value="progress"
          color="primary"
          class="q-mt-md"
        />
        <div class="text-center q-mt-sm">{{ progressMessage }}</div>
      </q-card-section>

      <q-card-section v-if="error" class="text-negative">
        {{ error }}
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
import { defineComponent, computed} from 'vue';

export default defineComponent({
  name: 'TrainingProgress',
  props: {
    show: Boolean,
    progress: Number,
    progressMessage: String,
    error: String,
  },
  setup(props, { emit }) {
    const dialogModel = computed({
      get: () => props.show,
      set: (value) => emit('update:show', value)
    });

    return {
      dialogModel,
    };
  }
});
</script>