<template>
    <div class="custom-layer-switcher">
        <p class="text-subtitle2 q-mb-sm">Layers</p>
        <div v-for="layer in mapStore.layers" :key="layer.id" class="layer-item q-mb-xs">
            <div class="row items-center no-wrap">
                <q-checkbox v-model="layer.visible" :label="layer.title"
                    @update:model-value="toggleLayerVisibility(layer.id)" dense class="col" />
                <q-btn flat round dense icon="tune" size="sm" @click="layer.showOpacity = !layer.showOpacity" />
            </div>
            <q-slide-transition>
                <div v-show="layer.showOpacity" class="opacity-slider q-mt-xs">
                    <q-slider
                        v-model="layer.opacity"
                        :min="0"
                        :max="1"
                        :step="0.1"
                        label
                        label-always
                        color="primary"
                        @update:model-value="updateLayerOpacity(layer.id, $event)"
                        dense
                    />
                </div>
            </q-slide-transition>
        </div>
    </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue';
import { useMapStore } from 'src/stores/mapStore';

export default {
    name: 'CustomLayerSwitcher',
    setup() {
        const mapStore = useMapStore();

        const toggleLayerVisibility = (layerId) => {
            mapStore.toggleLayerVisibility(layerId);
        };

        const updateLayerOpacity = (layerId, opacity) => {
            mapStore.updateLayerOpacity(layerId, opacity);
        };

        return {
            mapStore,
            toggleLayerVisibility,
            updateLayerOpacity
        };
    }
};
</script>

<style lang="scss" scoped>
.custom-layer-switcher {
    position: absolute;
    top: 10px;
    left: 10px;
    background-color: rgba(255, 255, 255, 0.9);
    padding: 10px;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    z-index: 1000;
    max-width: 250px;
}

.layer-item {
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 4px;

    &:last-child {
        border-bottom: none;
    }
}

.opacity-slider {
    padding-left: 28px; // Align with checkbox label
}
</style>