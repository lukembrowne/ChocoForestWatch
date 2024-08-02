<template>
    <div class="basemap-date-selector">
      <div v-for="(yearGroup, year) in groupedDates" :key="year" class="year-group">
        <div class="year-label">{{ year }}</div>
        <div class="month-columns">
          <div class="column">
            <q-radio
              v-for="option in yearGroup.slice(0, 6)"
              :key="option.value"
              v-model="selectedBasemapDate"
              :val="option.value"
              :label="option.label.split(' ')[0]"
              @update:model-value="onBasemapDateChange"

            />
          </div>
          <div class="column">
            <q-radio
              v-for="option in yearGroup.slice(6)"
              :key="option.value"
              v-model="selectedBasemapDate"
              :val="option.value"
              :label="option.label.split(' ')[0]"
              @update:model-value="onBasemapDateChange"

            />
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  import { computed, onMounted, onUnmounted } from 'vue'
  import { getBasemapDateOptions } from 'src/utils/dateUtils'
  import { useMapStore } from 'src/stores/mapStore'
  import { storeToRefs } from 'pinia'
  
  export default {
    name: 'BasemapDateSelector',
    setup() {
      const mapStore = useMapStore()
      const { selectedBasemapDate } = storeToRefs(mapStore)
  
      const dateOptions = getBasemapDateOptions()
  
      const groupedDates = computed(() => {
        return dateOptions.reduce((acc, option) => {
          const year = option.value.split('-')[0]
          if (!acc[year]) {
            acc[year] = []
          }
          acc[year].push(option)
          return acc
        }, {})
      })
  
      const handleKeyDown = (event) => {
        const currentIndex = dateOptions.findIndex(option => option.value === selectedBasemapDate.value)
        let newIndex
  
        if (event.key === 'ArrowUp') {
          newIndex = (currentIndex - 1 + dateOptions.length) % dateOptions.length
        } else if (event.key === 'ArrowDown') {
          newIndex = (currentIndex + 1) % dateOptions.length
        } else {
          return
        }
  
        mapStore.updateBasemap(dateOptions[newIndex].value)
      }



    const onBasemapDateChange = async (date) => {
      console.log("Basemap date changed to: ", date)
      console.log("Updating basemap")
      mapStore.updateBasemap(date)
    }

  
      onMounted(() => {
        window.addEventListener('keydown', handleKeyDown)
      })
  
      onUnmounted(() => {
        window.removeEventListener('keydown', handleKeyDown)
      })
  
      return {
        selectedBasemapDate,
        groupedDates,
        onBasemapDateChange
      }
    }
  }
  </script>
  
  <style scoped>
  .basemap-date-selector {
    overflow-y: auto;
  }
  .year-group {
    margin-bottom: 20px;
  }
  .year-label {
    font-weight: bold;
    margin-bottom: 10px;
  }
  .month-columns {
    display: flex;
    justify-content: space-between;
  }
  .column {
    width: 48%; /* Adjust as needed */
  }
  .q-radio {
    margin-bottom: 5px;
  }
  </style>