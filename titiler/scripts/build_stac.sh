#!/bin/bash

# --- Configuration ---
RCLONE_REMOTE_NAME="do-spaces"
BUCKET_NAME="choco-forest-watch"
# Base URL of your titiler-pgstac STAC API (from inside the same Docker network)
PGSTAC_URL="http://localhost:9090/stac"

process_month() {
    local month=$1
    local year=$2
    local BASE_S3_PATH="NICFI Monthly Mosaics/${year}/${month}"
    local temp_list
    local collection_id="NICFI-${year}-${month}"

    echo "----"
    echo "Processing month: ${month} for year: ${year}"
    echo "Creating/updating collection '${collection_id}' via HTTP…"

    # 1. Create or update the collection
    curl -s -X POST "${PGSTAC_URL}/collections" \
         -H "Content-Type: application/json" \
         -d '{
               "id": "'"${collection_id}"'",
               "description": "NICFI Monthly COG collection for '"${year}-${month}"'",
               "extent": {
                 "spatial": { "bbox": [] },
                 "temporal": { "interval": [] }
               }
             }' \
      && echo "  ✔ collection ${collection_id}"

    # 2. Build a temporary file listing all the COG URLs
    temp_list=$(mktemp)
    rclone lsf "${RCLONE_REMOTE_NAME}:${BUCKET_NAME}/${BASE_S3_PATH}/" \
        --include "*.tiff" --files-only --format "p" \
      | sed "s|^|s3://${BUCKET_NAME}/${BASE_S3_PATH}/|" \
      > "$temp_list"

    echo "Found COGs for ${collection_id}:"
    cat "$temp_list"

    # 3. Ingest each COG via the HTTP API
    echo "Ingesting COGs into collection ${collection_id}…"
    while read -r cog_url; do
      echo -n "  ➤ ${cog_url} … "
      # POST to /collections/{collection_id}/items with query params
      # asset_name=cog tells pgstac where to store the asset
      response=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${PGSTAC_URL}/collections/${collection_id}/items?asset_name=cog&href=${cog_url}")
      if [ "$response" -eq 200 ] || [ "$response" -eq 201 ]; then
        echo "OK"
      else
        echo "FAILED (HTTP $response)"
      fi
    done < "$temp_list"

    # 4. Clean up
    rm "$temp_list"
    echo "Done month ${year}-${month}"
}

# Process all months for 2022
for month in {01..12}; do
    process_month "$month" "2022"
done