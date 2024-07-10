<template>
  <q-page class="flex flex-center">
    <div class="container q-pa-md">
      <div class="row q-col-gutter-md">
        <div class="col-12 text-center">
          <h1 class="text-h3 q-mb-md text-weight-bold">Welcome to Choco Forest Watch</h1>
          <p class="text-h6 q-mb-xl">Empowering conservation through AI-driven forest monitoring</p>
        </div>

        <div class="col-12 col-md-4">
          <q-card class="my-card">
            <q-card-section>
              <div class="text-h6">About Choco Forest Watch</div>
              <p class="q-mt-md">
                Our application leverages cutting-edge machine learning techniques to analyze satellite imagery,
                enabling efficient monitoring and protection of the Chocó rainforest. By combining high-resolution
                satellite data with advanced AI models, we provide valuable insights for conservation efforts.
              </p>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-md-8">
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-4">
              <q-card class="my-card" v-ripple clickable @click="navigateTo('/training')">
                <q-card-section>
                  <div class="text-h6"><q-icon name="school" /> Training</div>
                  <p class="q-mt-md">Train XGBoost models for land cover classification using satellite imagery and labeled data.</p>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-md-4">
              <q-card class="my-card" v-ripple clickable @click="navigateTo('/prediction')">
                <q-card-section>
                  <div class="text-h6"><q-icon name="map" /> Prediction</div>
                  <p class="q-mt-md">Apply trained models to new satellite imagery to generate land cover classification maps.</p>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-md-4">
              <q-card class="my-card" v-ripple clickable @click="navigateTo('/analysis')">
                <q-card-section>
                  <div class="text-h6"><q-icon name="insert_chart" /> Analysis</div>
                  <p class="q-mt-md">Analyze land cover changes, generate reports, and create deforestation alerts.</p>
                </q-card-section>
              </q-card>
            </div>
          </div>
        </div>

        <div class="col-12 q-mt-xl">
          <q-card class="my-card bg-secondary text-white">
            <q-card-section>
              <div class="text-h6">Get Started</div>
              <p class="q-mt-md">
                Begin by training a model with your satellite imagery and ground truth data. Then use the trained model
                to predict land cover for new areas. Finally, analyze the results to gain insights into forest changes.
              </p>
              <q-btn color="white" text-color="secondary" label="Start New Project" @click="navigateTo('/training')" class="q-mt-sm" />
            </q-card-section>
          </q-card>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script>
import { defineComponent } from 'vue';
import { useRouter } from 'vue-router';

export default defineComponent({
  name: 'HomePage',
  setup() {
    const router = useRouter();

    const navigateTo = (path) => {
      router.push(path);
    };

    return {
      navigateTo
    };
  }
});
</script>

<style lang="scss" scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
}

.my-card {
  width: 100%;
  height: 100%;
}

.text-h3, .text-h6 {
  color: $primary;
}

.q-card {
  transition: all 0.3s ease-in-out;

  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
  }
}
</style>