<template>
  <q-dialog v-model="showModal">
    <q-card class="welcome-about-modal">
      <!-- Header with gradient background -->
      <q-card-section class="modal-header">
        <div class="header-content">
          <div class="header-icon">
            <q-icon name="park" />
          </div>
          <div class="header-text">
            <h1 class="modal-title">
              {{ isWelcomeMode ? t('welcome.modal.welcomeTitle') : t('about.title') }}
            </h1>
            <p v-if="isWelcomeMode" class="modal-subtitle">
              {{ t('welcome.modal.description') }}
            </p>
          </div>
        </div>
      </q-card-section>

      <!-- Scrollable content area -->
      <q-card-section class="modal-body">
        <!-- Welcome Content (only shown in welcome mode) -->
        <div v-if="isWelcomeMode" class="welcome-section">
          <div class="features-container">
            <h2 class="section-title">{{ t('welcome.modal.featuresTitle') }}</h2>
            <div class="features-grid">
              <div class="feature-card">
                <div class="feature-icon">
                  <q-icon name="satellite" />
                </div>
                <div class="feature-content">
                  <h3>{{ t('welcome.modal.features.imagery') }}</h3>
                  <p>{{ t('welcome.modal.descriptions.imagery') }}</p>
                </div>
              </div>
              
              <div class="feature-card">
                <div class="feature-icon">
                  <q-icon name="analytics" />
                </div>
                <div class="feature-content">
                  <h3>{{ t('welcome.modal.features.analysis') }}</h3>
                  <p>{{ t('welcome.modal.descriptions.analysis') }}</p>
                </div>
              </div>
              
              <div class="feature-card">
                <div class="feature-icon">
                  <q-icon name="code" />
                </div>
                <div class="feature-content">
                  <h3>{{ t('welcome.modal.features.openSource') }}</h3>
                  <p>{{ t('welcome.modal.descriptions.openSource') }}</p>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- About Content (always shown) -->
        <div class="about-section">
          <div class="about-intro">
            <p class="project-description">
              {{ t('about.description') }} 
              <a href="https://github.com/lukembrowne/chocoforestwatch" target="_blank" class="github-link">
                <q-icon name="open_in_new" size="sm" class="q-ml-xs" />
                {{ t('about.github') }}
              </a>.
            </p>
          </div>

          <div class="info-cards">
            <div class="info-card disclaimer-card">
              <div class="card-header">
                <q-icon name="warning" />
                <h3>{{ t('about.disclaimer.title') }}</h3>
              </div>
              <p>{{ t('about.disclaimer.text') }}</p>
            </div>

            <div class="info-card">
              <div class="card-header">
                <q-icon name="satellite" />
                <h3>{{ t('about.satellite.title') }}</h3>
              </div>
              <p>
                {{ t('about.satellite.description') }}
                <a href="https://planet.widen.net/s/zfdpf8qxwk/participantlicenseagreement_nicfi_2024" target="_blank" class="info-link">
                  {{ t('about.satellite.license') }}
                  <q-icon name="open_in_new" size="sm" class="q-ml-xs" />
                </a>.
              </p>
            </div>

            <div class="info-card">
              <div class="card-header">
                <q-icon name="notifications" />
                <h3>{{ t('about.alerts.title') }}</h3>
              </div>
              <p>
                {{ t('about.alerts.description') }}
                <a href="https://data.globalforestwatch.org/datasets/gfw::integrated-deforestation-alerts/about" target="_blank" class="info-link">
                  {{ t('about.alerts.license') }}
                  <q-icon name="open_in_new" size="sm" class="q-ml-xs" />
                </a>.
              </p>
            </div>

            <div class="info-card funding-card">
              <div class="card-header">
                <q-icon name="volunteer_activism" />
                <h3>{{ t('about.funding.title') }}</h3>
              </div>
              <p class="q-mb-sm">{{ t('about.funding.description') }}</p>
              <div class="funding-list">
                <div class="funding-item">{{ t('about.funding.sources.gfw') }}</div>
                <div class="funding-item">{{ t('about.funding.sources.yale') }}</div>
                <div class="funding-item">{{ t('about.funding.sources.tulane') }}</div>
                <div class="funding-item">{{ t('about.funding.sources.caids') }}</div>
              </div>
            </div>

            <div class="info-card version-card">
              <div class="card-header">
                <q-icon name="info" />
                <h3>{{ t('about.version.title') }}</h3>
              </div>
              <div class="version-info">
                <div class="version-item">
                  <span class="version-label">{{ t('about.version.number') }}:</span>
                  <span class="version-value">{{ version || 'Loading...' }}</span>
                </div>
                <!-- <div class="version-item">
                  <span class="version-label">{{ t('about.version.environment') }}:</span>
                  <span class="version-value">{{ environment || 'Loading...' }}</span>
                </div> -->
              </div>
            </div>
          </div>
        </div>
      </q-card-section>

      <!-- Sticky footer with actions -->
      <q-card-actions class="modal-footer">
        <div class="footer-content">
          <q-checkbox
            v-if="isWelcomeMode"
            v-model="dontShowAgain"
            :label="t('welcome.dontShowAgain')"
            class="dont-show-checkbox"
          />
          <div class="action-buttons">
            <q-btn
              unelevated
              size="lg"
              :label="isWelcomeMode ? t('welcome.modal.getStarted') : t('common.close')"
              color="primary"
              class="primary-button"
              @click="closeModal"
            />
          </div>
        </div>
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useWelcomeStore } from 'src/stores/welcomeStore';
import { useVersion } from 'src/composables/useVersion';

export default {
  name: 'WelcomeAboutModal',

  props: {
    mode: {
      type: String,
      default: 'about', // 'welcome' or 'about'
      validator: (value) => ['welcome', 'about'].includes(value)
    }
  },

  setup(props) {
    const { t } = useI18n();
    const dontShowAgain = ref(false);
    const welcomeStore = useWelcomeStore();
    const { version, environment } = useVersion();
    
    const isWelcomeMode = computed(() => props.mode === 'welcome');
    
    const showModal = computed({
      get: () => isWelcomeMode.value ? welcomeStore.showWelcomeModal : welcomeStore.showAboutModal,
      set: (value) => {
        if (isWelcomeMode.value) {
          welcomeStore.showWelcomeModal = value;
        } else {
          welcomeStore.showAboutModal = value;
        }
      }
    });

    const closeModal = () => {
      if (isWelcomeMode.value) {
        welcomeStore.closeWelcomeModal(dontShowAgain.value);
      } else {
        welcomeStore.showAboutModal = false;
      }
    };

    return {
      showModal,
      isWelcomeMode,
      dontShowAgain,
      closeModal,
      version,
      environment,
      t
    };
  }
};
</script>

<style lang="scss" scoped>
.welcome-about-modal {
  width: 900px;
  max-width: 95vw;
  max-height: 90vh;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

// Header section with gradient
.modal-header {
  background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 50%, #66BB6A 100%);
  color: white;
  padding: 32px 40px 24px;
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Ccircle cx='30' cy='30' r='1'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
    opacity: 0.5;
  }
}

.header-content {
  display: flex;
  align-items: center;
  gap: 20px;
  position: relative;
  z-index: 1;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 50%;
  backdrop-filter: blur(10px);
  
  .q-icon {
    font-size: 32px;
    color: white;
  }
}

.header-text {
  flex: 1;
}

.modal-title {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 8px 0;
  line-height: 1.2;
}

.modal-subtitle {
  font-size: 1.1rem;
  margin: 0;
  opacity: 0.95;
  line-height: 1.4;
  font-weight: 400;
}

// Scrollable body content
.modal-body {
  padding: 0;
  max-height: calc(90vh - 200px);
  overflow-y: auto;
  background: #fafafa;
}

// Welcome section styling
.welcome-section {
  padding: 40px;
  background: white;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #2E7D32;
  margin: 0 0 24px 0;
  text-align: center;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

.feature-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(46, 125, 50, 0.1);
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
    border-color: rgba(46, 125, 50, 0.2);
  }
}

.feature-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #4CAF50, #66BB6A);
  border-radius: 12px;
  margin-bottom: 16px;
  
  .q-icon {
    font-size: 24px;
    color: white;
  }
}

.feature-content {
  h3 {
    font-size: 1.1rem;
    font-weight: 600;
    color: #2E7D32;
    margin: 0 0 8px 0;
    line-height: 1.3;
  }
  
  p {
    font-size: 0.95rem;
    color: #666;
    margin: 0;
    line-height: 1.5;
  }
}

// Divider section
.divider-section {
  display: flex;
  align-items: center;
  gap: 20px;
  margin: 40px 0 32px;
  
  .q-separator {
    flex: 1;
    background: #e0e0e0;
  }
}

.divider-text {
  font-size: 1.1rem;
  font-weight: 600;
  color: #666;
  padding: 0 16px;
  white-space: nowrap;
}

// About section styling
.about-section {
  padding: 40px;
  background: #fafafa;
}

.project-description {
  font-size: 1.1rem;
  line-height: 1.6;
  color: #444;
  margin: 0 0 32px 0;
  text-align: center;
}

.github-link {
  color: #2E7D32;
  text-decoration: none;
  font-weight: 500;
  
  &:hover {
    text-decoration: underline;
  }
}

.info-cards {
  display: grid;
  gap: 20px;
}

.info-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  border-left: 4px solid #4CAF50;
  
  &.disclaimer-card {
    border-left-color: #FF9800;
    background: linear-gradient(135deg, #FFF3E0 0%, #FFFFFF 100%);
  }
  
  &.funding-card {
    border-left-color: #9C27B0;
  }
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  
  .q-icon {
    font-size: 24px;
    color: #4CAF50;
  }
  
  h3 {
    font-size: 1.2rem;
    font-weight: 600;
    color: #2E7D32;
    margin: 0;
  }
}

.disclaimer-card .card-header .q-icon {
  color: #FF9800;
}

.funding-card .card-header .q-icon {
  color: #9C27B0;
}

.info-card p {
  font-size: 0.95rem;
  line-height: 1.6;
  color: #555;
  margin: 0;
}

.info-link {
  color: #2E7D32;
  text-decoration: none;
  font-weight: 500;
  
  &:hover {
    text-decoration: underline;
  }
}

.funding-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.funding-item {
  background: #F3E5F5;
  color: #7B1FA2;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  text-align: center;
}

// Sticky footer
.modal-footer {
  background: white;
  border-top: 1px solid #e0e0e0;
  padding: 20px 40px;
  position: sticky;
  bottom: 0;
  z-index: 10;
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.05);
}

.footer-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.dont-show-checkbox {
  color: #666;
  font-size: 0.9rem;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.primary-button {
  min-width: 140px;
  height: 44px;
  font-weight: 600;
  border-radius: 8px;
  text-transform: none;
  font-size: 1rem;
  
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(76, 175, 80, 0.3);
  }
}

// Responsive design
@media (max-width: 1024px) {
  .welcome-about-modal {
    width: 95vw;
    max-height: 95vh;
  }
  
  .modal-header {
    padding: 24px 32px 20px;
  }
  
  .header-content {
    gap: 16px;
  }
  
  .header-icon {
    width: 56px;
    height: 56px;
    
    .q-icon {
      font-size: 28px;
    }
  }
  
  .modal-title {
    font-size: 1.75rem;
  }
  
  .welcome-section,
  .about-section {
    padding: 32px;
  }
  
  .features-grid {
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .modal-header {
    padding: 20px 24px 16px;
  }
  
  .header-content {
    flex-direction: column;
    text-align: center;
    gap: 12px;
  }
  
  .modal-title {
    font-size: 1.5rem;
  }
  
  .modal-subtitle {
    font-size: 1rem;
  }
  
  .welcome-section,
  .about-section {
    padding: 24px;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .feature-card {
    padding: 20px;
  }
  
  .modal-footer {
    padding: 16px 24px;
  }
  
  .footer-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .action-buttons {
    width: 100%;
    justify-content: center;
  }
  
  .primary-button {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .welcome-about-modal {
    width: 100vw;
    max-width: 100vw;
    height: 100vh;
    max-height: 100vh;
    border-radius: 0;
  }
  
  .modal-body {
    max-height: calc(100vh - 180px);
  }
  
  .welcome-section,
  .about-section {
    padding: 20px;
  }
  
  .funding-list {
    grid-template-columns: 1fr;
  }
}
</style>