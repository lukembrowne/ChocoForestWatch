<template>
  <q-card class="q-mt-md">
    <q-card-section>
      <div class="text-h6">{{ title }}</div>
      <q-table
        :rows="rows"
        :columns="columns"
        row-key="id"
        class="q-mt-md"
      >
        <template v-slot:body-cell-actions="props">
            <q-td>
            <q-checkbox
              :model-value="props.row.selected || false"
              @update:model-value="(value) => selectRow(props.row, value)"
              color="primary"
            />
          </q-td>
        </template>
      </q-table>
    </q-card-section>
  </q-card>
</template>

<script>
import { ref } from 'vue';

export default {
  name: 'DataTable',
  props: {
    title: {
      type: String,
      required: true
    },
    rows: {
      type: Array,
      required: true
    },
    columns: {
      type: Array,
      required: true
    }
  },
  emits: ['row-selected'],
  setup(props, { emit }) {
    const selectRow = (row, value) => {
      emit('row-selected', { ...row, selected: value });
    };

    return {
      selectRow
    };
  }
};
</script>