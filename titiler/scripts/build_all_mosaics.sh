#!/bin/bash

# --- Configuration ---
# Your rclone remote name for DigitalOcean Spaces
RCLONE_REMOTE_NAME="do-spaces" # Or whatever you named it in your rclone config

# Your DigitalOcean Spaces bucket name
BUCKET_NAME="choco-forest-watch"

# Output directory for mosaicJSON files
MOSAIC_OUTPUT_DIR="../mosaicJsons"
mkdir -p "$MOSAIC_OUTPUT_DIR"


process_month() {
    local month=$1
    local year=$2
    local output_file="/mosaicJsons/${year}-${month}.json"
    local BASE_S3_PATH="NICFI Monthly Mosaics/${year}/${month}"


    echo "Processing month: ${month} for year: ${year}"


    # --- Script Logic ---
    local temp_list=$(mktemp)
    local output_file="${MOSAIC_OUTPUT_DIR}/${year}-${month}-mosaic.json"

    echo "Looking for COGs in s3://${BUCKET_NAME}/${BASE_S3_PATH}/ for ${year}-${month}"

    # Use rclone lsf to list files and create S3 URIs
    # The --files-only flag ensures we only list files, not directories.
    # The --format "p" gives the path relative to the listed directory.
    # We then prepend the full S3 URI.
    rclone lsf "${RCLONE_REMOTE_NAME}:${BUCKET_NAME}/${BASE_S3_PATH}/" \
        --include "*.tiff" \
        --files-only \
        --format "p" | sed "s|^|s3://${BUCKET_NAME}/${BASE_S3_PATH}/|" > "$temp_list"

    # Print out the temp list for verification
    echo "Generated list of S3 URIs:"
    cat "$temp_list"

    # Save the temp list to a file (optional, for debugging)
    cat "$temp_list" > "${MOSAIC_OUTPUT_DIR}/${year}-${month}-cog-list.txt"

    # Check if we found any COGs
    if [ -s "$temp_list" ] && [ "$(wc -l < "$temp_list")" -gt 0 ]; then
        echo "Found $(wc -l < "$temp_list") COGs in ${year}-${month}"

        # Need to ensure the environment variables for S3 authentication are set or else this won't work
        echo "Creating mosaicJSON with cogeo-mosaic..."
        cogeo-mosaic create "$temp_list" \
            --minzoom 8 \
            --maxzoom 14 \
            --output "$output_file" 

        if [ $? -eq 0 ]; then
            echo "Successfully created mosaic at ${output_file}"
        else
            echo "Error creating mosaicJSON. Check cogeo-mosaic output."
        fi
    else
        echo "No COGs found in s3://${BUCKET_NAME}/${BASE_S3_PATH}/ for ${year}-${month}"
    fi

    # Clean up temp file
    rm "$temp_list"

    echo "Script finished for ${year}-${month}"
}


# Process all months for 2022
for month in {01..12}; do
    process_month "$month" "2022"
done

# Process all months for 2023
# for month in {01..12}; do
#     process_month "$month" "2023"
# done

# # Process all months for 2024
# for month in {01..12}; do
#     process_month "$month" "2024"
# done