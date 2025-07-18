import { defineStore } from 'pinia';
import { ref } from 'vue';
import authService from 'src/services/auth';

export const useWelcomeStore = defineStore('welcome', () => {
  const showProjectsModal = ref(false);
  const showTrainingModal = ref(false);
  const showAnalysisModal = ref(false);
  const showWelcomeModal = ref(false);
  const showAboutModal = ref(false);

  const showHelp = (section) => {
    const isAdmin = authService.getCurrentUser()?.user?.is_superuser === true;
    if (!isAdmin) return;
    console.log('Showing help for section:', section);
    switch(section) {
      case 'projects':
        showProjectsModal.value = true;
        break;
      case 'training':
        showTrainingModal.value = true;
        break;
      case 'analysis':
        showAnalysisModal.value = true;
        break;
      default:
        console.warn('Unknown section:', section);
    }
  };

  const checkWelcomeModalStatus = () => {
    const isAdmin = authService.getCurrentUser()?.user?.is_superuser === true;
    if (isAdmin) return; // Don't show welcome modal for admin users
    
    // Check localStorage for welcome modal preference
    const hasSeenWelcome = localStorage.getItem('seen_welcome_modal');
    if (!hasSeenWelcome) {
      showWelcomeModal.value = true;
    }
  };

  const closeWelcomeModal = (dontShowAgain = false) => {
    showWelcomeModal.value = false;
    if (dontShowAgain) {
      localStorage.setItem('seen_welcome_modal', 'true');
    }
  };

  const openAboutModal = () => {
    showAboutModal.value = true;
  };

  return {
    showProjectsModal,
    showTrainingModal,
    showAnalysisModal,
    showWelcomeModal,
    showAboutModal,
    showHelp,
    checkWelcomeModalStatus,
    closeWelcomeModal,
    openAboutModal
  };
}); 