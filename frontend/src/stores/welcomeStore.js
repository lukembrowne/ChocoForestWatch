import { defineStore } from 'pinia';
import { ref } from 'vue';
import api from 'src/services/api';

export const useWelcomeStore = defineStore('welcome', () => {
  const showProjectsModal = ref(false);
  const showTrainingModal = ref(false);
  const showAnalysisModal = ref(false);

  const showHelp = (section) => {
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
    }
  };

  return {
    showProjectsModal,
    showTrainingModal,
    showAnalysisModal,
    showHelp
  };
}); 