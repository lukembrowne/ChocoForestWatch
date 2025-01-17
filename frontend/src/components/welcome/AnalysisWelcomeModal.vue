<template>
  <q-dialog v-model="showModal">
    <q-card class="welcome-modal">
      <q-card-section class="bg-primary text-white">
        <div class="text-h6">{{ t('welcome.analysis.title') }}</div>
      </q-card-section>

      <q-card-section class="q-pa-md">
        <div class="text-body1 q-mb-md">
          {{ t('welcome.analysis.intro') }}
        </div>

        <div class="key-features q-gutter-y-md">
          <!-- Choose Dates -->
          <div class="feature-item">
            <q-icon name="date_range" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.analysis.chooseDates.title') }}</div>
              <div class="text-caption">{{ t('welcome.analysis.chooseDates.description') }}</div>
            </div>
          </div>

          <!-- Run Analysis -->
          <div class="feature-item">
            <q-icon name="analytics" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.analysis.run.title') }}</div>
              <div class="text-caption">{{ t('welcome.analysis.run.description') }}</div>
            </div>
          </div>

          <!-- Verify Hotspots -->
          <div class="feature-item">
            <q-icon name="check_circle" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.analysis.verify.title') }}</div>
              <div class="text-caption">{{ t('welcome.analysis.verify.description') }}</div>
            </div>
          </div>

          <!-- View Summary and Export -->
          <div class="feature-item">
            <q-icon name="insert_chart" color="primary" size="sm" class="q-mr-sm" />
            <div>
              <div class="text-weight-medium">{{ t('welcome.analysis.summary.title') }}</div>
              <div class="text-caption">{{ t('welcome.analysis.summary.description') }}</div>
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
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import api from 'src/services/api';
import { useWelcomeStore } from 'src/stores/welcomeStore';

export default {
  name: 'AnalysisWelcomeModal',

  setup() {
    const { t } = useI18n();
    const dontShowAgain = ref(false);
    const welcomeStore = useWelcomeStore();
    const showModal = computed({
      get: () => welcomeStore.showAnalysisModal,
      set: (value) => welcomeStore.showAnalysisModal = value
    });

    onMounted(async () => {
      try {
        const response = await api.getUserSettings();
        if (!response.data.seen_welcome_analysis) {
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
            seen_welcome_analysis: true
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
  width: 800px;
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