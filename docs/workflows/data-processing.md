# Data Processing Workflow

This document describes the one-time processing used to prepare NICFI (Norway's International Climate and Forests Initiative) satellite imagery for use in ChocoForestWatch.

## Overview

The workflow transfers NICFI imagery from external storage, builds STAC metadata, and loads the catalog into PGSTAC so TiTiler can serve tiles and the backend can query collections consistently.

## Steps

1. Data Transfer
   - Use `scripts/migrate_nicfi_data.sh` to transfer NICFI imagery from Google Drive to DigitalOcean Spaces (or other object storage).
   - Best to run this script directly on the Droplet for efficiency
   - Handles reliable transfer of large datasets.

2. STAC Integration
   - Process the transferred imagery using `scripts/build_nicfi_STAC.py`.
   - Builds SpatioTemporal Asset Catalog (STAC) metadata for each asset.
   - Inserts STAC records into the PGSTAC database.
   - Enables seamless integration with TiTiler for dynamic tile serving and standardized access via STAC API endpoints.

## Related Paths

- Scripts: `scripts/migrate_nicfi_data.sh`, `scripts/build_nicfi_STAC.py`
- Database: PGSTAC (configured via `docker-compose.yml`)
- Tile server: TiTiler service in `titiler-pgstac/`

## Notes

- This workflow is typically performed once per imagery drop. Re-run it only when adding new imagery or regenerating metadata.

