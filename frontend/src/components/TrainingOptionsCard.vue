<template>
    <q-card style="width: 400px; max-width: 90vw;">
        <q-card-section>
            <div class="text-h6">XGBoost Model Training Options</div>
        </q-card-section>

        <q-card-section>
            <q-form @submit="onSubmit">
                <div class="q-mb-md">
                    <div class="text-subtitle2">Number of Estimators</div>
                    <q-slider v-model="options.n_estimators" :min="10" :max="1000" :step="10" label label-always
                        color="primary" />
                    <div class="text-caption">The number of trees in the forest. Higher values generally improve
                        performance but increase training time.</div>
                </div>

                <div class="q-mb-md">
                    <div class="text-subtitle2">Max Depth</div>
                    <q-slider v-model="options.max_depth" :min="1" :max="10" :step="1" label label-always
                        color="primary" />
                    <div class="text-caption">Maximum depth of the trees. Higher values make the model more complex and
                        prone to overfitting.</div>
                </div>

                <div class="q-mb-md">
                    <div class="text-subtitle2">Learning Rate</div>
                    <q-slider v-model="options.learning_rate" :min="0.01" :max="0.3" :step="0.01" label label-always
                        color="primary" />
                    <div class="text-caption">Step size shrinkage used to prevent overfitting. Lower values are
                        generally better but require more iterations.</div>
                </div>

                <div class="q-mb-md">
                    <div class="text-subtitle2">Min Child Weight</div>
                    <q-slider v-model="options.min_child_weight" :min="1" :max="10" :step="1" label label-always
                        color="primary" />
                    <div class="text-caption">Minimum sum of instance weight needed in a child. Higher values make the
                        model more conservative.</div>
                </div>

                <div class="q-mb-md">
                    <div class="text-subtitle2">Gamma</div>
                    <q-slider v-model="options.gamma" :min="0" :max="1" :step="0.1" label label-always
                        color="primary" />
                    <div class="text-caption">Minimum loss reduction required to make a further partition. Higher values
                        make the model more conservative.</div>
                </div>
            </q-form>
        </q-card-section>

        <q-card-actions align="right">
            <q-btn flat label="Cancel" color="primary" v-close-popup />
            <q-btn flat label="Train Model" color="primary" @click="onSubmit" />
        </q-card-actions>
    </q-card>
</template>

<script>
import { ref } from 'vue';

export default {
    name: 'TrainingOptionsCard',
    emits: ['train', 'close'],
    setup(props, { emit }) {
        const options = ref({
            n_estimators: 100,
            max_depth: 3,
            learning_rate: 0.1,
            min_child_weight: 1,
            gamma: 0,
        });

        const onSubmit = () => {
            emit('train', options.value);
            emit('close');
        };

        return {
            options,
            onSubmit,
        };
    },
};
</script>