<template>
  <q-dialog v-model="showModal">
    <q-card class="welcome-modal">
      <q-card-section class="bg-primary text-white">
        <div class="text-h6">{{ t('welcome.projects.title') }}</div>
      </q-card-section>

      <q-card-section class="q-pa-md">
        <div class="text-body1 q-mb-md">
          {{ t('welcome.projects.intro') }}
        </div>

        <div class="key-features q-gutter-y-md">
          <!-- Create Project -->
          <div class="feature-item">
            <q-icon name="add" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.projects.create.title') }}</div>
              <div class="text-caption">{{ t('welcome.projects.create.description') }}</div>
            </div>
          </div>

          <!-- Define AOI -->
          <div class="feature-item">
            <q-icon name="map" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.projects.aoi.title') }}</div>
              <div class="text-caption">{{ t('welcome.projects.aoi.description') }}</div>
            </div>
          </div>

          <!-- Configure -->
          <div class="feature-item">
            <q-icon name="settings" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.projects.configure.title') }}</div>
              <div class="text-caption">{{ t('welcome.projects.configure.description') }}</div>
            </div>
          </div>
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
  width: 500px;
  max-width: 90vw;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  padding: 8px;
  border-radius: 4px;
  
  &:hover {
    background: rgba(0,0,0,0.03);
  }
}
</style> 