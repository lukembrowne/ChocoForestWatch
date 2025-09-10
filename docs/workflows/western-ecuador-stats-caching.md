# Western Ecuador Statistics Caching

The application includes an optimized caching system for Western Ecuador summary statistics across different forest cover datasets. As of 2025, all datasets are pre-processed and clipped to Western Ecuador, enabling much faster calculation through simplified pixel counting without geometric boundary clipping.

## Key Features

- Simplified calculation using direct pixel counting (1=forest, 0=non-forest, 255=missing)
- Auto-loading on the homepage for instant statistics
- Instant access after pre-calculation warms the cache
- Memory efficient compared to prior boundary-based approach

## Pre-calculation Scripts

To ensure instant loading, pre-calculate statistics for all datasets.

### Using Django Management Command (Recommended)

```bash
# Pre-calculate all statistics using optimized simplified mode
docker compose exec backend python manage.py precalculate_western_ecuador_stats --db-host local

# Force recalculation even if cached
docker compose exec backend python manage.py precalculate_western_ecuador_stats --force --db-host local

# Calculate for specific collection only
docker compose exec backend python manage.py precalculate_western_ecuador_stats --collection datasets-hansen-tree-cover-2022 --db-host local

# Clear all cached stats before calculating
docker compose exec backend python manage.py precalculate_western_ecuador_stats --clear --db-host local

# Test with first collection only (recommended for troubleshooting)
docker compose exec backend python manage.py precalculate_western_ecuador_stats --test-first --db-host local

# Combine options for fresh calculation
docker compose exec backend python manage.py precalculate_western_ecuador_stats --clear --force --db-host local
```

### Using Standalone Script

```bash
# Pre-calculate all statistics (from project root)
python scripts/precalculate_stats.py

# Force recalculation even if cached
python scripts/precalculate_stats.py --force

# Calculate for specific collection only
python scripts/precalculate_stats.py --collection datasets-hansen-tree-cover-2022

# Show help
python scripts/precalculate_stats.py --help
```

## Available Forest Cover Collections

The available datasets are managed dynamically through the database system. Current collections include:

- `datasets-hansen-tree-cover-2022` — Hansen Global Forest Change
- `datasets-mapbiomas-2022` — MapBiomas Ecuador
- `datasets-esa-landcover-2020` — ESA WorldCover
- `datasets-jrc-forestcover-2020` — JRC Forest Cover
- `datasets-palsar-2020` — ALOS PALSAR Forest Map
- `datasets-wri-treecover-2020` — WRI Tropical Tree Cover
- `datasets-cfw-{run_id}-{year}` — ChocoForestWatch model predictions

For the complete list of available datasets, use the Django admin interface at `/admin/core/dataset/` or query the API at `/api/datasets/`.

## Caching Details

- Storage: File-based cache in `backend/djangocfw/cache/`
- Persistence: Statistics survive server restarts
- Timeout: Never expires (cached indefinitely)
- Automatic loading: Frontend displays cached regional stats when datasets are selected
- Fallback: If cache is empty, statistics are calculated on-demand and then cached

## Troubleshooting

If the pre-calculation seems to hang or fail:

1. Test with one collection first:
   ```bash
   docker compose exec backend python manage.py precalculate_western_ecuador_stats --test-first --db-host local
   ```
2. Monitor detailed logs while running:
   ```bash
   docker compose logs -f backend
   ```
3. Verify environment variables:
   - `TITILER_URL` should be set (usually `http://tiler-uvicorn:8083`)
4. Common issues:
   - TiTiler service not running
   - Network timeouts
   - Invalid collection IDs in STAC database
   - Collection statistics endpoint not available (falls back to default values)
5. Performance expectations:
   - Simplified mode: typically 10–30 seconds per collection
   - Standard mode (fallback): 1–2 minutes per collection

## Environment Requirements

- `TITILER_URL` — URL of the TiTiler service (e.g., `http://tiler-uvicorn:8083`)

Note: `BOUNDARY_GEOJSON_PATH` is no longer required for the simplified calculation mode since all datasets are pre-processed.

## Recommended Workflow

1. After deployment or major updates, run the pre-calculation script to warm the cache
2. Users will then see instant Western Ecuador statistics when they select different forest cover datasets
3. Users can still draw custom areas to override the default regional statistics

