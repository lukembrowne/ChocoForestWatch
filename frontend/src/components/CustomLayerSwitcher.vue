<template>
    <div class="custom-layer-switcher">
        <p>Layers</p>
        <div v-for="layer in mapStore.layers" :key="layer.id" class="layer-item">
            <q-checkbox v-model="layer.visible" :label="layer.title"
                @update:model-value="toggleLayerVisibility(layer.id)" />
            <q-slider
                v-model="layer.opacity"
                :min="0"
                :max="1"
                :step="0.1"
                label
                label-always
                color="primary"
                @update:model-value="updateLayerOpacity(layer.id, $event)"
                class="q-mt-xs"
            />
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

<style scoped>
.custom-layer-switcher {
    position: absolute;
    top: 10px;
    left: 10px;
    background-color: white;
    padding: 10px;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
    z-index: 1000;
}

.layer-item {
    margin-bottom: 5px;
}
</style>