<template>
  <q-layout view="hHh Lpr fFf">
    <q-header elevated>
      <q-toolbar>
        <q-toolbar-title>
          Choco Forest Watch
        </q-toolbar-title>
        <q-btn flat label="Model Training" @click="navigateTo('model-training')" />
        <q-btn flat label="Prediction" @click="navigateTo('prediction')" />
        <q-btn flat label="Analysis" @click="navigateTo('analysis')" />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script>
export default {
  name: 'MainLayout',
  methods: {
    navigateTo(path) {
      this.$router.push({ path });
    }
  }
};
</script>