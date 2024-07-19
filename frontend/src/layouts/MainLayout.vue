<template>
  <q-layout view="hHh LpR fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>Choco Forest Watch</q-toolbar-title>
        <q-tabs>
          <q-route-tab to="/" label="Home" icon="home" />
          <q-route-tab to="/debug" label="Debug" icon="insert_chart" />

        </q-tabs>
      </q-toolbar>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" side="left" bordered>
      <workflow-sidebar />
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>

   
  </q-layout>
</template>

<script>
import { ref } from 'vue'
import WorkflowSidebar from 'components/WorkflowSidebar.vue'

export default {
  name: 'MainLayout',
  components: {
    WorkflowSidebar
  },
  setup () {
    const leftDrawerOpen = ref(true)

    return {
      leftDrawerOpen
    }
  }
}
</script>