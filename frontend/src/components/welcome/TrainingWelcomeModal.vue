<template>
  <q-dialog v-model="showModal">
    <q-card class="welcome-modal">
      <q-card-section class="bg-primary text-white">
        <div class="text-h6">{{ t('welcome.training.title') }}</div>
      </q-card-section>

      <q-card-section class="q-pa-md">
        <div class="text-body1 q-mb-md">
          {{ t('welcome.training.intro') }}
        </div>

        <div class="key-features q-gutter-y-md">
          <!-- Satellite Imagery Selection -->
          <div class="feature-item">
            <q-icon name="map" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.training.sections.imagery.title') }}</div>
              <div class="text-caption">{{ t('welcome.training.sections.imagery.description') }}</div>
            </div>
          </div>

          <!-- Training Data Collection -->
          <div class="feature-item">
            <q-icon name="edit" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.training.sections.training.title') }}</div>
              <div class="text-caption">{{ t('welcome.training.sections.training.description') }}</div>
            </div>
          </div>

          <!-- Drawing Tools -->
          <div class="feature-item">
            <q-icon name="gesture" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.training.sections.drawing.title') }}</div>
              <div class="text-caption">{{ t('welcome.training.sections.drawing.description') }}</div>
            </div>
          </div>

          <!-- Model Training -->
          <div class="feature-item">
            <q-icon name="school" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.training.sections.model.title') }}</div>
              <div class="text-caption">{{ t('welcome.training.sections.model.description') }}</div>
            </div>
          </div>

          <!-- Analysis -->
          <div class="feature-item">
            <q-icon name="insights" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.training.sections.analysis.title') }}</div>
              <div class="text-caption">{{ t('welcome.training.sections.analysis.description') }}</div>
            </div>
          </div>

          <!-- Data Access -->
          <div class="feature-item">
            <q-icon name="cloud_download" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.training.sections.access.title') }}</div>
              <div class="text-caption">{{ t('welcome.training.sections.access.description') }}</div>
            </div>
          </div>

          <!-- Example Screenshot -->
          <!-- <div class="feature-item">
            <q-icon name="image" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.training.sections.example.title') }}</div>
              <div class="text-caption">
                <q-img 
                  src="/images/training-example.jpeg" 
                  :alt="t('welcome.training.sections.example.description')" 
                  style="max-width: 100%; border-radius: 4px; margin-top: 8px;" 
                  class="rounded-borders" 
                />
              </div>
            </div>
          </div> -->
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
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import api from 'src/services/api';
import { useWelcomeStore } from 'src/stores/welcomeStore';

export default {
  name: 'TrainingWelcomeModal',

  setup() {
    const { t } = useI18n();
    const dontShowAgain = ref(false);
    const welcomeStore = useWelcomeStore();
    const showModal = computed({
      get: () => welcomeStore.showTrainingModal,
      set: (value) => welcomeStore.showTrainingModal = value
    });

    onMounted(async () => {
      try {
        const response = await api.getUserSettings();
        if (!response.data.seen_welcome_training) {
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
            seen_welcome_training: true
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
  width: 750px;
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