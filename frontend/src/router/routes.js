import UploadData from '../components/UploadData.vue'
import DrawPolygons from '../components/DrawPolygons.vue'
import ReviewPolygons from '../components/ReviewPolygons.vue'
// import TrainModel from '../components/TrainModel.vue'
// import PredictLandUse from '../components/PredictLandUse.vue'
// import VisualizeResults from '../components/VisualizeResults.vue'

export default [
  { path: '/upload', component: UploadData },
  { path: '/draw', component: DrawPolygons },
  { path: '/review', component: ReviewPolygons },
  // { path: '/train', component: TrainModel },
  // { path: '/predict', component: PredictLandUse },
  // { path: '/visualize', component: VisualizeResults },
  { path: '/', redirect: '/upload' } // Redirect to upload page by default
]