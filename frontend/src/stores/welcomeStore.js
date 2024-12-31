import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useWelcomeStore = defineStore('welcome', () => {
  const showProjectsModal = ref(false);
  const showTrainingModal = ref(false);
  const showAnalysisModal = ref(false);

  const showHelp = (section) => {
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

  return {
    showProjectsModal,
    showTrainingModal,
    showAnalysisModal,
    showHelp
  };
}); 