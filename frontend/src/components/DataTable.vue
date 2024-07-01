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
              <q-btn dense flat label="Select" color="primary" @click="selectRow(props.row)" />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </template>
  
  <script>
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
      const selectRow = (row) => {
        emit('row-selected', row);
      };
  
      return {
        selectRow
      };
    }
  };
  </script>