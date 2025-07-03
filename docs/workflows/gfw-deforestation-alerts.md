# GFW Integrated Deforestation Alerts

## Overview

The Global Forest Watch (GFW) Integrated Deforestation Alerts system provides near real-time forest disturbance detection for the ChocoForestWatch platform. This feature replaces the previous polygon-based approach with a more efficient raster-based system that supports interactive point queries.

## Architecture

### Data Source
- **Provider**: Global Forest Watch (WRI)
- **Dataset**: GFW Integrated Alerts (GLAD, RADD, and other systems)
- **Coverage**: Global (Ecuador subset for CFW)
- **Resolution**: 10m pixels
- **Update Frequency**: Near real-time

### Implementation Approach
- **Storage**: Raster tiles served via TiTiler/STAC infrastructure
- **Interaction**: Click-to-query functionality for alert details
- **Years**: 2022, 2023, 2024 (expandable)
- **Format**: Cloud Optimized GeoTIFF (COG)

## Data Processing Pipeline

### 1. Raw Data Acquisition
The system downloads GFW alert tiles covering Ecuador using the GFW API:

```bash
cd ml_pipeline/notebooks
poetry run python process_gfw_alerts.py --years 2022 2023 2024
```

**GFW Tiles for Ecuador:**
- `10N_080W` - Northern Ecuador, western region
- `00N_080W` - Southern Ecuador, western region  
- `00N_090W` - Southern Ecuador, eastern region
- `10N_090W` - Northern Ecuador, eastern region

### 2. Processing Steps

1. **Download**: Fetch raw alert tiles from GFW API
2. **Boundary Clipping**: Clip tiles to Ecuador administrative boundary
3. **Temporal Filtering**: Extract alerts for specific years (2022-2024)
4. **Merging**: Combine multiple tiles into seamless mosaics
5. **Optimization**: Create Cloud Optimized GeoTIFFs for efficient serving
6. **STAC Integration**: Automatically create STAC collections for tile serving

### 3. Storage Structure

```
datasets/gfw-integrated-alerts/
├── 2022/
│   └── gfw_integrated_alerts_2022_ecuador.tif
├── 2023/
│   └── gfw_integrated_alerts_2023_ecuador.tif
└── 2024/
    └── gfw_integrated_alerts_2024_ecuador.tif
```

**STAC Collections:**
- `datasets-gfw-integrated-alerts-2022`
- `datasets-gfw-integrated-alerts-2023`
- `datasets-gfw-integrated-alerts-2024`

## Pixel Value Encoding

GFW alerts use a compact encoding system where each pixel value contains both temporal and confidence information:

### Encoding Format
- **First Digit**: Confidence level (1-4)
  - `1` = Low confidence
  - `2` = Medium confidence
  - `3` = High confidence
  - `4` = Very high confidence
- **Remaining Digits**: Days since December 31, 2014

### Example
- **Pixel Value**: `32850`
- **Decoded**: Confidence 3 (High), Alert Date: November 15, 2022
- **Calculation**: 2014-12-31 + 2850 days = 2022-11-15

### Decoding Implementation
```javascript
// Frontend decoding function
const decodeGFWDate = (value) => {
  if (value === 0) return { date: null, confidence: null };
  
  const encoded_str = value.toString();
  const confidence = parseInt(encoded_str[0]);
  const days = parseInt(encoded_str.substring(1));
  
  const baseDate = new Date(2014, 11, 31);
  const alertDate = new Date(baseDate.getTime() + days * 24 * 60 * 60 * 1000);
  
  return { date: alertDate, confidence: confidence };
};
```

## Frontend Integration

### Dataset Selection
GFW alerts appear in the dataset selector alongside forest cover datasets:

- **Type**: `alerts` (distinct from `benchmark` and `prediction`)
- **Visualization**: Binary display (red pixels for detected alerts)
- **Interaction**: Click any alert pixel to see details

### User Interaction Flow
1. **Selection**: User selects GFW alerts dataset from dropdown
2. **Display**: Raster layer loads showing alert pixels in red
3. **Query**: User clicks on alert pixel
4. **Response**: Popup shows decoded date and confidence level

### Translation Support
The system supports both English and Spanish:

```json
// English (en.json)
"alerts": {
  "title": "GFW Deforestation Alerts",
  "description": "Integrated deforestation alerts from Global Forest Watch...",
  "url": "https://www.globalforestwatch.org/help/map/guides/forest-change-analysis/"
}

// Spanish (es.json)  
"alerts": {
  "title": "Alertas de Deforestación GFW",
  "description": "Alertas integradas de deforestación de Global Forest Watch...",
  "url": "https://www.globalforestwatch.org/help/map/guides/forest-change-analysis/"
}
```

## Configuration

### Environment Variables
Add to both `.env` and `.env.prod`:

```bash
# Global Forest Watch API
GFW_API_KEY=your_api_key_here
```

### Processing Parameters
```python
# Years to process
YEARS = [2022, 2023, 2024]

# Ecuador boundary file
BOUNDARY_PATH = "ml_pipeline/notebooks/boundaries/Ecuador-DEM-900m-contour.geojson"

# Output directory
OUTPUT_DIR = "gfw_alerts_output"
```

## Usage Examples

### Process All Years
```bash
cd ml_pipeline/notebooks
poetry run python process_gfw_alerts.py --years 2022 2023 2024 --output-dir gfw_alerts_output
```

### Force Re-download
```bash
poetry run python process_gfw_alerts.py --years 2022 --force-download
```

### Custom Output Directory
```bash
poetry run python process_gfw_alerts.py --years 2023 --output-dir custom_output
```

## Performance Optimizations

### Parallel Processing
- **Multi-core**: Utilizes up to 8 CPU cores for pixel processing
- **Chunking**: Processes data in chunks for memory efficiency
- **Progress Tracking**: Real-time progress reporting every 5%

### Caching Strategy
- **Local Cache**: Downloaded tiles cached to avoid re-downloading
- **Persistent Storage**: Cached tiles don't expire (historical data)
- **Smart Reuse**: Checks cache before downloading

### Memory Management
- **Streaming**: Processes tiles individually to limit memory usage
- **Cleanup**: Automatic cleanup of temporary files
- **Context Manager**: Proper resource management with Python context managers

## Troubleshooting

### Common Issues

1. **Network Errors**: Check internet connection and GFW API status
2. **Missing Boundary**: Ensure Ecuador boundary file exists at expected path
3. **API Key**: Verify `GFW_API_KEY` environment variable is set
4. **Memory**: Reduce parallel workers if experiencing memory issues

### Debug Output
```bash
# Verbose logging
poetry run python process_gfw_alerts.py --years 2022 --output-dir debug_output
```

### Log Analysis
Look for these key log messages:
- `"Processing tile {tile_id} for year {year}"`
- `"Found {count} alert pixels for {year}"`
- `"Parallel processing complete"`
- `"Uploaded to S3: {key}"`

## Migration from Polygon System

### Advantages of Raster Approach
- **Performance**: No vector polygon rendering bottlenecks
- **Accuracy**: Preserves exact pixel-level alert information
- **Scalability**: Handles larger datasets without frontend issues
- **Consistency**: Follows same pattern as other raster datasets

### Deprecation Notice
The Django-based polygon service (`gfw_alerts.py`) has been removed. The new raster-based approach should be used for all future development.

## Future Enhancements

### Planned Features
- **Additional Years**: Extend coverage beyond 2024
- **Real-time Updates**: Automated processing of new alerts
- **Multi-region Support**: Expand beyond Ecuador boundary
- **Alert Notifications**: Email/webhook notifications for new alerts

### Technical Improvements
- **Incremental Updates**: Process only new/changed data
- **Compression**: Further optimize COG compression
- **Metadata**: Enhanced STAC metadata for discoverability
- **API Integration**: Direct API endpoints for alert queries

## References

- [Global Forest Watch Alerts Documentation](https://www.globalforestwatch.org/help/map/guides/forest-change-analysis/)
- [GFW Integrated Alerts Dataset](https://data.globalforestwatch.org/datasets/gfw::integrated-deforestation-alerts/about)
- [TiTiler Documentation](https://stac-utils.github.io/titiler-pgstac/)
- [STAC Specification](https://stacspec.org/)