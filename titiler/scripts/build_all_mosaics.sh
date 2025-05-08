#!/bin/bash

# Create mosaics directory if it doesn't exist
mkdir -p /mosaics

# Function to process a single month's COGs
process_month() {
    local month=$1
    local year=$2
    local month_dir="/data/${year}/${month}"
    local output_file="/mosaics/${year}-${month}.json"
    
    if [ -d "$month_dir" ]; then
        echo "Processing ${year}/${month}"
        
        # Find all .tif files in the directory and create a temporary list
        local temp_list="/tmp/${year}-${month}_cogs.txt"
        find "$month_dir" -type f -name "*.tif" > "$temp_list"
        
        # Check if we found any COGs
        if [ -s "$temp_list" ]; then
            echo "Found $(wc -l < "$temp_list") COGs in ${year}-${month}"
            cogeo-mosaic create "$temp_list" \
                --minzoom 8 \
                --maxzoom 14 \
                --output "$output_file" \
                --quiet
            echo "Created mosaic at ${output_file}"
        else
            echo "No COGs found in ${year}-${month}"
        fi
        
        # Clean up temporary file
        rm -f "$temp_list"
    else
        echo "Directory not found: ${year}-${month}"
    fi
}

# Process all months for 2022
for month in {01..12}; do
    process_month "$month" "2022"
done

    # Process all months for 2023
for month in {01..12}; do
    process_month "$month" "2023"
done

# Process all months for 2024
for month in {01..12}; do
    process_month "$month" "2024"
done    

echo "All mosaics have been created!" 