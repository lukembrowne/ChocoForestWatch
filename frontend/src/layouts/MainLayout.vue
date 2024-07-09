<template>
  <q-layout view="hHh Lpr fFf">
    <q-header elevated>
      <q-toolbar>
        <q-toolbar-title>
          Choco Forest Watch
        </q-toolbar-title>
        <q-tabs>
          <q-route-tab to="/" label="Landing Page" />
          <q-route-tab to="/map" label="Map Page" />
          <q-route-tab to="/model-training" label="Model Training" />
          <q-route-tab to="/prediction" label="Prediction" />
        </q-tabs>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script>
export default {
  name: 'MainLayout'
};
</script>