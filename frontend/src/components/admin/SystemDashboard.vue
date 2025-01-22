<template>
  <div class="system-dashboard q-pa-md">
    <div class="text-h5 q-mb-lg">System Dashboard</div>

    <!-- Summary Cards -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-sm-6 col-md-4">
        <q-card class="bg-primary text-white">
          <q-card-section>
            <div class="text-h4">{{ stats.total_users }}</div>
            <div class="text-subtitle2">Total Users</div>
            <div class="text-caption">{{ stats.active_users_30d }} active in last 30 days</div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-sm-6 col-md-4">
        <q-card class="bg-secondary text-white">
          <q-card-section>
            <div class="text-h4">{{ stats.total_projects }}</div>
            <div class="text-subtitle2">Total Projects</div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-sm-6 col-md-4">
        <q-card class="bg-accent text-white">
          <q-card-section>
            <div class="text-h4">{{ formatArea(stats.total_area_ha) }}</div>
            <div class="text-subtitle2">Total Area Monitored</div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-sm-6 col-md-4">
        <q-card class="bg-negative text-white">
          <q-card-section>
            <div class="text-h4">{{ formatArea(stats.total_deforestation_area) }}</div>
            <div class="text-subtitle2">Total Deforestation Detected</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12">
        <q-card>
          <q-card-section>
            <div class="text-h6 q-mb-md">Recent Activity (Last 30 Days)</div>
            <div class="row q-col-gutter-md">
              <div class="col-4">
                <div class="text-subtitle2">New Projects</div>
                <div class="text-h5">{{ stats.recent_activity?.new_projects || 0 }}</div>
              </div>
              <div class="col-4">
                <div class="text-subtitle2">Models Trained</div>
                <div class="text-h5">{{ stats.recent_activity?.models_trained || 0 }}</div>
              </div>
              <div class="col-4">
                <div class="text-subtitle2">Hotspots Verified</div>
                <div class="text-h5">{{ stats.recent_activity?.hotspots_verified || 0 }}</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Detailed Statistics -->
    <div class="row q-col-gutter-md">
      <!-- Models Over Time -->
      <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Models Trained (Last 30 Days)</div>
            <div class="chart-container">
              <bar-chart v-if="modelChartData" 
                :data="modelChartData"
                :options="chartOptions"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Hotspot Verification Status -->
      <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Hotspot Verification Status</div>
            <div class="chart-container">
              <pie-chart v-if="hotspotChartData"
                :data="hotspotChartData"
                :options="chartOptions"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Deforestation by Status -->
      <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Deforestation by Status</div>
            <div class="chart-container">
              <bar-chart v-if="deforestationChartData"
                :data="deforestationChartData"
                :options="chartOptions"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Hotspots by Source -->
      <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Hotspots by Source</div>
            <div class="chart-container">
              <pie-chart v-if="hotspotSourceChartData"
                :data="hotspotSourceChartData"
                :options="chartOptions"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { Bar as BarChart, Pie as PieChart } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, ArcElement } from 'chart.js';
import api from 'src/services/api';

// Register ChartJS components
ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, ArcElement);

export default {
  name: 'SystemDashboard',
  components: { BarChart, PieChart },

  setup() {
    const stats = ref({
      total_users: 0,
      total_projects: 0,
      total_models: 0,
      total_area_ha: 0,
      total_hotspots: 0,
      active_users_30d: 0,
      projects_by_class: [],
      hotspots_by_status: [],
      models_by_date: [],
      total_deforestation_area: 0,
      deforestation_by_status: [],
      hotspots_by_source: [],
      hotspots_by_source_and_status: [],
      recent_activity: {
        models_trained: 0,
        hotspots_verified: 0,
        new_projects: 0
      }
    });

    const formatArea = (area) => {
      if (area >= 1000000) {
        return `${(area / 1000000).toFixed(1)}M ha`;
      } else if (area >= 1000) {
        return `${(area / 1000).toFixed(1)}K ha`;
      }
      return `${area.toFixed(1)} ha`;
    };

    const modelChartData = computed(() => {
      if (!stats.value.models_by_date?.length) return null;
      return {
        labels: stats.value.models_by_date.map(d => d.date),
        datasets: [{
          label: 'Models Trained',
          data: stats.value.models_by_date.map(d => d.count),
          backgroundColor: '#1976D2'
        }]
      }
    });

    const hotspotChartData = computed(() => {
      if (!stats.value.hotspots_by_status?.length) return null;
      return {
        labels: stats.value.hotspots_by_status.map(h => h.verification_status || 'Unverified'),
        datasets: [{
          data: stats.value.hotspots_by_status.map(h => h.count),
          backgroundColor: ['#4CAF50', '#FFC107', '#607D8B', '#9E9E9E']
        }]
      }
    });

    const deforestationChartData = computed(() => {
      if (!stats.value.deforestation_by_status?.length) return null;
      return {
        labels: stats.value.deforestation_by_status.map(d => d.verification_status || 'Unverified'),
        datasets: [{
          label: 'Area (ha)',
          data: stats.value.deforestation_by_status.map(d => d.area),
          backgroundColor: '#FF5252'
        }]
      }
    });

    const hotspotSourceChartData = computed(() => {
      if (!stats.value.hotspots_by_source?.length) return null;
      return {
        labels: stats.value.hotspots_by_source.map(h => h.source.toUpperCase()),
        datasets: [{
          data: stats.value.hotspots_by_source.map(h => h.count),
          backgroundColor: ['#1976D2', '#FF5252']
        }]
      }
    });

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'bottom'
        }
      }
    };

    const loadStatistics = async () => {
      try {
        const response = await api.getSystemStatistics();
        console.log("Response from loadStatistics", response);
        stats.value = response.data;
      } catch (error) {
        console.error('Error loading system statistics:', error);
      }
    };

    onMounted(() => {
      loadStatistics();
      // Refresh every 5 minutes
      setInterval(loadStatistics, 300000);
    });

    return {
      stats,
      formatArea,
      modelChartData,
      hotspotChartData,
      chartOptions,
      deforestationChartData,
      hotspotSourceChartData
    };
  }
};
</script>

<style lang="scss" scoped>
.system-dashboard {
  .chart-container {
    height: 300px;
  }
}
</style> 