<template>
  <q-layout view="hHh LpR fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-btn dense flat round icon="menu" @click="toggleLeftDrawer" />
        <q-toolbar-title>
          Choco Forest Watch
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-drawer show-if-above v-model="leftDrawerOpen" side="left" bordered>
      <q-list>
        <q-item-label header>Navigation</q-item-label>
        <q-item clickable v-ripple to="/" exact>
          <q-item-section avatar>
            <q-icon name="home" />
          </q-item-section>
          <q-item-section>Home</q-item-section>
        </q-item>
        <q-item clickable v-ripple to="/project-setup">
          <q-item-section avatar>
            <q-icon name="add_circle" />
          </q-item-section>
          <q-item-section>Project Setup</q-item-section>
        </q-item>
        <q-item clickable v-ripple to="/data-preparation">
          <q-item-section avatar>
            <q-icon name="map" />
          </q-item-section>
          <q-item-section>Data Preparation</q-item-section>
        </q-item>
        <q-item clickable v-ripple to="/model-training">
          <q-item-section avatar>
            <q-icon name="school" />
          </q-item-section>
          <q-item-section>Model Training</q-item-section>
        </q-item>
        <q-item clickable v-ripple to="/prediction">
          <q-item-section avatar>
            <q-icon name="insights" />
          </q-item-section>
          <q-item-section>Prediction</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script>
import { ref } from 'vue';

export default {
  name: 'MainLayout',
  setup() {
    const leftDrawerOpen = ref(false);

    const toggleLeftDrawer = () => {
      leftDrawerOpen.value = !leftDrawerOpen.value;
    };

    return {
      leftDrawerOpen,
      toggleLeftDrawer
    };
  }
};
</script>