<template>
  <q-dialog v-model="showModal">
    <q-card class="welcome-modal">
      <q-card-section class="bg-primary text-white">
        <div class="text-h6">{{ t('welcome.projects.title') }}</div>
      </q-card-section>

      <q-card-section class="q-pa-md">
        <div class="text-body1 q-mb-lg">
          {{ t('welcome.projects.intro') }}
        </div>

        <div class="workflow-steps q-gutter-y-md">
          <!-- Create Project -->
          <div class="workflow-step">
            <div class="step-number">1</div>
            <div class="step-content">
              <div class="text-weight-medium">{{ t('welcome.projects.create.title') }}</div>
              <div class="text-body2">{{ t('welcome.projects.create.description') }}</div>
            </div>
          </div>

          <!-- Define AOI -->
          <div class="workflow-step">
            <div class="step-number">2</div>
            <div class="step-content">
              <div class="text-weight-medium">{{ t('welcome.projects.aoi.title') }}</div>
              <div class="text-body2">{{ t('welcome.projects.aoi.description') }}</div>
            </div>
          </div>

          <!-- Train Model -->
          <div class="workflow-step">
            <div class="step-number">3</div>
            <div class="step-content">
              <div class="text-weight-medium">{{ t('welcome.projects.train.title') }}</div>
              <div class="text-body2">{{ t('welcome.projects.train.description') }}</div>
            </div>
          </div>

          <!-- Analysis -->
          <div class="workflow-step">
            <div class="step-number">4</div>
            <div class="step-content">
              <div class="text-weight-medium">{{ t('welcome.projects.analysis.title') }}</div>
              <div class="text-body2">{{ t('welcome.projects.analysis.description') }}</div>
            </div>
          </div>
        </div>

        <q-separator class="q-my-md" />

        <div class="text-body2 q-mb-md">
          {{ t('welcome.projects.landcover') }}
        </div>

        <div class="text-body2 q-mb-md">
          {{ t('welcome.projects.feedback') }}
        </div>
      </q-card-section>

      <q-card-actions align="right" class="bg-white">
        <q-checkbox
          v-model="dontShowAgain"
          :label="t('welcome.dontShowAgain')"
          class="q-mr-sm"
        />
        <q-btn
          flat
          :label="t('common.getStarted')"
          color="primary"
          @click="closeModal"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import api from 'src/services/api';
import { useWelcomeStore } from 'src/stores/welcomeStore';

export default {
  name: 'ProjectsWelcomeModal',

  setup() {
    const { t } = useI18n();
    const dontShowAgain = ref(false);
    const welcomeStore = useWelcomeStore();
    const showModal = computed({
      get: () => welcomeStore.showProjectsModal,
      set: (value) => welcomeStore.showProjectsModal = value
    });

    onMounted(async () => {
      try {
        const response = await api.getUserSettings();
        if (!response.data.seen_welcome_projects) {
          showModal.value = true;
        }
      } catch (error) {
        console.error('Error checking welcome modal status:', error);
      }
    });

    const closeModal = async () => {
      if (dontShowAgain.value) {
        try {
          await api.updateUserSettings({
            seen_welcome_projects: true
          });
        } catch (error) {
          console.error('Error updating welcome modal status:', error);
        }
      }
      showModal.value = false;
    };

    return {
      showModal,
      dontShowAgain,
      closeModal,
      t
    };
  }
};
</script>

<style lang="scss" scoped>
.welcome-modal {
  width: 600px;
  max-width: 90vw;
}

.workflow-step {
  display: flex;
  align-items: flex-start;
  padding: 12px;
  border-radius: 8px;
  background: rgba(0,0,0,0.02);
  
  &:hover {
    background: rgba(0,0,0,0.05);
  }
}

.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--q-primary);
  color: white;
  font-weight: bold;
  margin-right: 12px;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}
</style> 