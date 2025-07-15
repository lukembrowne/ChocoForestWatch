# Scripts Directory

This directory contains utility scripts for the Choco Forest Watch project.

## Western Ecuador Statistics Pre-calculation

### Django Management Command

```bash
# Pre-calculate all statistics (using Docker)
docker compose exec backend python manage.py precalculate_western_ecuador_stats

# Force recalculation even if cached
docker compose exec backend python manage.py precalculate_western_ecuador_stats --force

# Calculate for specific collection only
docker compose exec backend python manage.py precalculate_western_ecuador_stats --collection datasets-hansen-tree-cover-2022

# Clear all cached stats before calculating
docker compose exec backend python manage.py precalculate_western_ecuador_stats --clear

# Combine options
docker compose exec backend python manage.py precalculate_western_ecuador_stats --clear --force
```

### Standalone Script

```bash
# Pre-calculate all statistics (from project root)
python scripts/precalculate_stats.py

# Force recalculation even if cached
python scripts/precalculate_stats.py --force

# Calculate for specific collection only
python scripts/precalculate_stats.py --collection datasets-hansen-tree-cover-2022

# Clear all cached stats before calculating
python scripts/precalculate_stats.py --clear

# Show help
python scripts/precalculate_stats.py --help
```

## Available Collections

The following benchmark collections are supported:

- `datasets-hansen-tree-cover-2022` - Hansen Global Forest Change
- `datasets-mapbiomas-2022` - MapBiomas Ecuador
- `datasets-esa-landcover-2020` - ESA WorldCover
- `datasets-jrc-forestcover-2020` - JRC Forest Cover
- `datasets-palsar-2020` - ALOS PALSAR Forest Map
- `datasets-wri-treecover-2020` - WRI Tropical Tree Cover
- `nicfi-pred-northern_choco_test_2025_06_16-composite-2022` - Choco Forest Watch 2022

## Environment Requirements

The following environment variables must be set:

- `TITILER_URL` - URL of the TiTiler service
- `BOUNDARY_GEOJSON_PATH` - Path to the western Ecuador boundary GeoJSON file

## Caching

Statistics are cached to disk using Django's file-based cache backend. The cache location is configured in Django settings and defaults to `backend/djangocfw/cache/`.

Cached statistics persist across server restarts and have a default timeout of 30 days.