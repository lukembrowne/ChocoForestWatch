<template>
    <q-page padding>
        <h3>Welcome to Choco Forest Watch</h3>

        <div class="q-pa-md">
            <file-upload-card data-type="Raster" accepted-file-types=".tif,.tiff"
                @file-uploaded="handleRasterUploaded" />
            <file-upload-card data-type="Vector" accepted-file-types=".geojson" @file-uploaded="handleVectorUploaded" />

            <data-table title="Available Rasters" :rows="rasters" :columns="rasterColumns"
                @row-selected="handleRasterSelection" />

            <data-table title="Available Vectors" :rows="vectors" :columns="vectorColumns"
                @row-selected="handleVectorSelection" />

        </div>

        <div>
            <p v-if="selectedRaster">Selected Raster: ID: {{ selectedRaster.id }} Filename: {{ selectedRaster.filename
                }} Description: {{ selectedRaster.description }}</p>
            <p v-if="selectedVector">Selected Vector: ID: {{ selectedVector.id }} Filename: {{ selectedVector.filename
                }}</p>
        </div>

        <q-btn label="Proceed to Map" color="positive" class="q-mt-lg" :disable="!canProceed" @click="proceedToMap" />
    </q-page>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import apiService from '../services/api';
import FileUploadCard from '../components/FileUploadCard.vue';
import DataTable from '../components/DataTable.vue';

export default {
    name: 'LandingPage',
    components: {
        FileUploadCard,
        DataTable
    },
    setup() {
        const rasters = ref([]);
        const vectors = ref([]);
        const selectedRaster = ref(null);
        const selectedVector = ref(null);
        const router = useRouter();


        const fetchData = async () => {
            try {
                const [rasterResponse, vectorResponse] = await Promise.all([
                    apiService.fetchRasters(),
                    apiService.fetchVectors()
                ]);
                rasters.value = rasterResponse.data;
                vectors.value = vectorResponse.data;
            } catch (error) {
                console.error('Error fetching data:', error);
                // TODO: Show error message to user
            }
        };

        onMounted(fetchData);

        const handleRasterUploaded = () => {
            fetchData();
            // TODO: Show success message to user
        };

        const handleVectorUploaded = () => {
            fetchData();
            // TODO: Show success message to user
        };

        const selectRaster = (raster) => {
            selectedRaster.value = raster;
        };

        const selectVector = (vector) => {
            selectedVector.value = vector;
        };

        const handleRasterSelection = (updatedRow) => {
            const index = rasters.value.findIndex(row => row.id === updatedRow.id);
            if (index !== -1) {
                rasters.value[index] = updatedRow;
            }
            // Do something with the selected row
            console.log('Updated row:', updatedRow);
            selectedRaster.value = updatedRow;
        };

        const handleVectorSelection = (updatedRow) => {
            const index = vectors.value.findIndex(row => row.id === updatedRow.id);
            if (index !== -1) {
                vectors.value[index] = updatedRow;
            }
            // Do something with the selected row
            console.log('Updated row:', updatedRow);
            selectedVector.value = updatedRow;

        };

        const canProceed = computed(() => {
            return selectedRaster.value !== null;
        });

        const proceedToMap = () => {
            router.push({
                name: 'map',
                params: {
                    rasterId: selectedRaster.value.id,
                    polygonSetId: selectedVector.value ? selectedVector.value.id : 'new'
                }
            });
        };

        return {
            rasters,
            vectors,
            selectedRaster,
            selectedVector,
            handleRasterUploaded,
            handleVectorUploaded,
            selectRaster,
            selectVector,
            handleRasterSelection,
            handleVectorSelection,
            canProceed,
            proceedToMap,
            rasterColumns: [
                { name: 'id', required: true, label: 'ID', align: 'left', field: 'id', sortable: true },
                { name: 'filename', required: true, label: 'Filename', align: 'left', field: 'filename', sortable: true },
                { name: 'description', required: true, label: 'Description', align: 'left', field: 'description', sortable: true },
                { name: 'actions', label: 'Select', field: 'actions', align: 'left' }
            ],
            vectorColumns: [
                { name: 'id', required: true, label: 'ID', align: 'left', field: 'id', sortable: true },
                { name: 'filename', required: true, label: 'Filename', align: 'left', field: 'filename', sortable: true },
                { name: 'description', required: true, label: 'Description', align: 'left', field: 'description', sortable: true },
                { name: 'actions', label: 'Select', field: 'actions', align: 'left' }
            ]
        };
    }
};
</script>