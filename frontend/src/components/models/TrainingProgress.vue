<template>
  <q-dialog v-model="dialogModel" persistent>
    <q-card style="min-width: 300px">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ t('training.modelTraining.progress.title') }}</div>
        <q-space />
        <q-btn
          icon="close"
          flat
          round
          dense
          @click="handleCancel"
          :disable="progress >= 100"
        >
          <q-tooltip>{{ t('training.modelTraining.progress.tooltips.cancel') }}</q-tooltip>
        </q-btn>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-linear-progress
          :value="progress / 100"
          color="primary"
          class="q-mt-md"
        />
        <div class="text-center q-mt-sm">{{ progressMessage }}</div>
      </q-card-section>

      <q-card-section v-if="error" class="text-negative">
        {{ error }}
      </q-card-section>

      <q-card-section v-if="progress >= 100" class="text-center">
        <q-btn color="primary" :label="t('training.modelTraining.progress.close')" @click="closeDialog" />
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script>
import { defineComponent, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';

export default defineComponent({
  name: 'TrainingProgress',
  props: {
    show: Boolean,
    progress: Number,
    progressMessage: String,
    error: String,
  },
  emits: ['update:show', 'cancel', 'complete'],
  setup(props, { emit }) {
    const { t } = useI18n();
    const dialogModel = computed({
      get: () => props.show,
      set: (value) => emit('update:show', value)
    });

    const handleCancel = () => {
      emit('cancel');
    };

    const closeDialog = () => {
      dialogModel.value = false;
      emit('complete');
    };

    watch(() => props.progress, (newProgress) => {
      if (newProgress >= 100) {
        setTimeout(() => {
          closeDialog();
        }, 2000);
      }
    });

    return {
      dialogModel,
      handleCancel,
      closeDialog,
      t
    };
  }
});
</script>