<template>
  <q-layout view="hHh Lpr fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>Choco Forest Watch</q-toolbar-title>
        <q-tabs>
          <q-route-tab to="/" label="Home" icon="home" />
          <q-route-tab to="/training" label="Training" icon="school" />
          <q-route-tab to="/prediction" label="Prediction" icon="map" />
          <q-route-tab to="/analysis" label="Analysis" icon="insert_chart" />
          <q-route-tab to="/debug" label="Debug" icon="insert_chart" />

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
}
</script>