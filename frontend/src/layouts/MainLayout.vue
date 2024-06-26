<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
      <q-toolbar>
        <q-toolbar-title>
          Choco Forest Watch
        </q-toolbar-title>

        <q-btn flat label="Upload Data" @click="goTo('/upload')" />
        <q-btn flat label="Draw Polygons" @click="goTo('/draw')" />
        <q-btn flat label="Review Polygons" @click="goTo('/review')" />
        <q-btn flat label="Train Model" @click="goTo('/train')" />
        <q-btn flat label="Predict Land Use" @click="goTo('/predict')" />
        <q-btn flat label="Visualize Results" @click="goTo('/visualize')" />

        <q-space />

        <div></div>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goTo(route) {
  router.push(route)
}
</script>