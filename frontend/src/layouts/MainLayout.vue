<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
      <q-toolbar>
        <q-btn
          flat
          dense
          round
          icon="menu"
          aria-label="Menu"
          @click="toggleLeftDrawer"
        />

        <q-toolbar-title>
          Choco Forest Watch
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="leftDrawerOpen"
      show-if-above
      bordered
    >
      <q-list>
        <q-item to="/model-training" clickable v-ripple>
          <q-item-section>
            <q-item-label>Model Training</q-item-label>
          </q-item-section>
        </q-item>
        <q-item to="/prediction" clickable v-ripple>
          <q-item-section>
            <q-item-label>Prediction</q-item-label>
          </q-item-section>
        </q-item>
        <q-item to="/analysis" clickable v-ripple>
          <q-item-section>
            <q-item-label>Analysis</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref } from 'vue'

const leftDrawerOpen = ref(false)

function toggleLeftDrawer () {
  leftDrawerOpen.value = !leftDrawerOpen.value
}
</script>