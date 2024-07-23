<template>
    <div class="custom-layer-switcher">
        <p>Layers</p>
        <div v-for="layer in mapStore.layers" :key="layer.id" class="layer-item">
            <q-checkbox v-model="layer.visible" :label="layer.title"
                @update:model-value="toggleLayerVisibility(layer.id)" />
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

        return {
            mapStore,
            toggleLayerVisibility
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
    border-radius: 4px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
    z-index: 1000;
}

.layer-item {
    margin-bottom: 5px;
}
</style>