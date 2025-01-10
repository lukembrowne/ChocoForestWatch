<template>
    <div class="basemap-date-slider">
        <!-- <p class="text-subtitle1" style="margin: 0; padding: 0;">{{ t('layers.basemapDate.title') }}</p> -->
        <div class="slider-container">
            <!-- Add help icon with tooltip -->
            <div class="help-icon">
                <q-btn
                    flat
                    round
                    dense
                    icon="help"
                    size="sm"
                    color="primary"
                >
                    <q-tooltip>
                        {{ t('layers.basemapDate.tooltip') }}
                    </q-tooltip>
                </q-btn>
            </div>

            <div class="year-markers">
                <div v-for="year in years" :key="year" class="year-marker"
                    :style="{ left: `${getYearPosition(year)}%` }">
                    {{ year }}
                </div>
            </div>
            <q-slider v-model="sliderValue" :min="0" :max="dates.length - 1" :step="1" label
                :label-value="formatDate(selectedDate)" @update:model-value="updateSelectedDate">
                <template v-slot:thumb>
                    <q-icon name="place" color="primary" />
                </template>
            </q-slider>
            <div class="month-markers">
                <div v-for="(date, index) in dates" :key="index" class="month-marker"
                    :class="{ 'has-data': hasTrainingData(date), 'excluded': isDateExcluded(date) }">
                    {{ formatMonth(date) }}
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useMapStore } from 'src/stores/mapStore';
import { useProjectStore } from 'src/stores/projectStore';
import { getBasemapDateOptions } from 'src/utils/dateUtils';
import { useI18n } from 'vue-i18n';

export default {
    name: 'BasemapDateSlider',
    setup() {
        const { t } = useI18n();
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

            window.addEventListener('keydown', handleKeyDown)

        });

        const hasTrainingData = (date) => {
            return projectStore.hasTrainingData(date);
        };

        const isDateExcluded = (date) => {
            return projectStore.isDateExcluded(date);
        };

        const updateSelectedDate = async (value) => {
            console.log("Updating selected date with argument:", value);

            // If unsaved changes, prompt to save
            if (hasUnsavedChanges.value) {
                await mapStore.promptSaveChanges();
            }

            mapStore.updateBasemap(dates.value[value]);

            // Load training polygons for the selected date
            console.log("Loading training polygons for date:", dates.value[value]);
            mapStore.loadTrainingPolygonsForDate(dates.value[value]);
        };

        const formatDate = (date) => {
            const [year, month] = date.split('-');
            const monthNames = [
                t('layers.basemapDate.months.jan'),
                t('layers.basemapDate.months.feb'),
                t('layers.basemapDate.months.mar'),
                t('layers.basemapDate.months.apr'),
                t('layers.basemapDate.months.may'),
                t('layers.basemapDate.months.jun'),
                t('layers.basemapDate.months.jul'),
                t('layers.basemapDate.months.aug'),
                t('layers.basemapDate.months.sep'),
                t('layers.basemapDate.months.oct'),
                t('layers.basemapDate.months.nov'),
                t('layers.basemapDate.months.dec')
            ];
            return `${monthNames[parseInt(month) - 1]} - ${year}`;
        };

        const formatMonth = (date) => {
            const [, month] = date.split('-');
            return month;
        };

        const getYearPosition = (year) => {
            const yearStart = dates.value.findIndex(date => date.startsWith(year));
            return (yearStart / (dates.value.length - 1)) * 100;
        };

        const handleKeyDown = (event) => {

            const currentIndex = dates.value.findIndex(option => option === mapStore.selectedBasemapDate)
            let newIndex

            if (event.key === 'ArrowLeft') {
                newIndex = (currentIndex - 1 + dates.value.length) % dates.value.length
            } else if (event.key === 'ArrowRight') {
                newIndex = (currentIndex + 1) % dates.value.length
            } else {
                return
            }

            console.log("dates.value[newIndex]:", dates.value[newIndex]);
            updateSelectedDate(newIndex)
            sliderValue.value = newIndex
        }

        onUnmounted(() => {
            window.removeEventListener('keydown', handleKeyDown)
        })

        // Add a watcher for the mapStore's sliderValue
        watch(() => mapStore.sliderValue, (newValue) => {
            sliderValue.value = newValue;
        });

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
            isDateExcluded,
            t
        };
    },
};
</script>

<style scoped>
:root {
  --basemap-date-slider-height: 100px; /* Adjust this value based on the actual height of your slider */
}

.basemap-date-slider {
    position: absolute;
    bottom: 10px;
    width: 100%;
    background-color: rgba(255, 255, 255, 0.95);
    padding: 5px 20px 5px 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    z-index: 1001;
    height: var(--basemap-date-slider-height);
}

.current-date {
    text-align: center;
    font-size: 1.2em;
    font-weight: bold;
    margin-bottom: 0px;
}

.slider-container {
    position: relative;
    padding: 10px 0;
}

.year-markers {
    position: absolute;
    top: 0;
    left: 10px;
    right: 0;
    height: 20px;
}

.year-marker {
    position: absolute;
    transform: translateX(-50%);
    font-size: 0.9em;
    font-weight: 500;
}

.month-markers {
    display: flex;
    justify-content: space-between;
    margin-top: 0px;
}

.month-marker {
    font-size: 0.9em;
    color: #888;
    width: 10px;
    text-align: center;
}

.month-marker.has-data {
    font-weight: 1000;
    color: #4CAF50;
    text-decoration: underline;
}

.month-marker.excluded {
    color: #ff0000;
    text-decoration: line-through;
}

.q-slider {
    height: 10px;
}

.q-slider__track-container {
    background-color: #e0e0e0;
}

.q-slider__track {
    background-color: #4CAF50;
}

.q-slider__thumb {
    background-color: #4CAF50;
    width: 10px;
    height: 10px;
}

.slider-container {
    padding: 15px 0 0 0;
}

.help-icon {
    position: absolute;
    top: -10px;
    right: 0px;
    z-index: 1;
}
</style>