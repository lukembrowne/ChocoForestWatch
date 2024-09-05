<template>
    <div class="basemap-date-slider">
        <div class="slider-container">
            <div class="year-markers">
                <div v-for="year in years" :key="year" class="year-marker"
                    :style="{ left: `${getYearPosition(year)}%` }">
                    {{ year }}
                </div>
            </div>
            <q-slider v-model="sliderValue" :min="0" :max="dates.length - 1" :step="1" label label-always
                :label-value="formatDate(selectedDate)" @update:model-value="updateSelectedDate">
                <template v-slot:thumb>
                    <q-icon name="place" color="primary" />
                </template>
            </q-slider>
            <div class="month-markers">
                <div v-for="(date, index) in dates" :key="index" class="month-marker"
                    :class="{ 'has-data': hasTrainingData(date) }">
                    {{ formatMonth(date) }}
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useMapStore } from 'src/stores/mapStore';
import { getBasemapDateOptions } from 'src/utils/dateUtils';
import { useProjectStore } from 'src/stores/projectStore';

export default {
    name: 'BasemapDateSlider',
    setup() {
        const mapStore = useMapStore();
        const projectStore = useProjectStore();
        const dates = ref(getBasemapDateOptions().map(option => option.value));
        const sliderValue = ref(0);
        const selectedDate = computed(() => dates.value[sliderValue.value]);

        const years = computed(() => {
            const uniqueYears = new Set(dates.value.map(date => date.split('-')[0]));
            return Array.from(uniqueYears);
        });

        const hasUnsavedChanges = computed(() => mapStore.hasUnsavedChanges);

        onMounted(async () => {
            if (projectStore.currentProject) {
                console.log("Fetching training dates for project:", projectStore.currentProject.id);
                await projectStore.fetchTrainingDates();
            }
        });

        const hasTrainingData = (date) => {
            return projectStore.hasTrainingData(date);
        };

        const updateSelectedDate = async (value) => {
            console.log("hasUnsavedChanges within updateSelectedDate:", hasUnsavedChanges.value);

            // If unsaved changes, prompt to save
            if (hasUnsavedChanges.value) {
                await mapStore.promptSaveChanges();
            }

            mapStore.updateBasemap(dates.value[value]);

            // Load training polygons for the selected date
            mapStore.loadTrainingPolygonsForDate(dates.value[value]);
        };

        const formatDate = (date) => {
            const [year, month] = date.split('-');
            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            return `${monthNames[parseInt(month) - 1]} ${year}`;
        };

        const formatMonth = (date) => {
            const [, month] = date.split('-');
            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            return monthNames[parseInt(month) - 1];
        };

        const getYearPosition = (year) => {
            const yearStart = dates.value.findIndex(date => date.startsWith(year));
            return (yearStart / (dates.value.length - 1)) * 100;
        };

        return {
            sliderValue,
            selectedDate,
            dates,
            years,
            updateSelectedDate,
            formatDate,
            formatMonth,
            getYearPosition,
            hasTrainingData,
        };
    },
};
</script>

<style scoped>
.basemap-date-slider {
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    width: 50%;
    background-color: rgba(255, 255, 255, 0.95);
    padding: 10px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.current-date {
    text-align: center;
    font-size: 1.2em;
    font-weight: bold;
    margin-bottom: 10px;
}

.slider-container {
    position: relative;
    padding: 20px 0;
}

.year-markers {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 20px;
}

.year-marker {
    position: absolute;
    transform: translateX(-50%);
    font-size: 0.8em;
    color: #666;
}

.month-markers {
    display: flex;
    justify-content: space-between;
    margin-top: 5px;
}

.month-marker {
    font-size: 0.9em;
    color: #888;
    width: 20px;
    text-align: center;
}

.month-marker.has-data {
    font-weight: bold;
    color: #4CAF50;
}

.q-slider {
    height: 40px;
}

.q-slider__track-container {
    background-color: #e0e0e0;
}

.q-slider__track {
    background-color: #4CAF50;
}

.q-slider__thumb {
    background-color: #4CAF50;
    width: 20px;
    height: 20px;
}
</style>