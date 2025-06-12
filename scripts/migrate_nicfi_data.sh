#!/bin/bash

# Script to migrate NICFI Monthly Mosaics from Google Drive to DigitalOcean Spaces
# Usage: ./migrate_nicfi_data.sh
# Requirements: rclone, tmux

set -e  # Exit on error

# Start a new tmux session if not already in one
if [ -z "$TMUX" ]; then
    tmux new-session -d -s migrate
    tmux attach-session -t migrate
fi

# Define years and months
YEARS=("2022")
MONTHS=("01" "02" "03" "04" "05" "06" "07" "08" "09" "10" "11" "12")

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to get first 10 files from a directory
get_first_10_files() {
    local year=$1
    local month=$2
    local source_dir="gdrive:GIS/Satellite imagery/Planet imagery/NICFI Monthly Mosaics/${year}/${month}/"
    
    # Use rclone ls to list files and extract just the filenames
    rclone ls "$source_dir" | head -n 10 | awk '{print $2}'
}

# Main migration loop
for YEAR in "${YEARS[@]}"; do
    for MONTH in "${MONTHS[@]}"; do
        log "Getting files for ${YEAR}/${MONTH}..."
        
        # Get the first 10 files for this year/month
        mapfile -t FILES < <(get_first_10_files "$YEAR" "$MONTH")
        
        for FILENAME in "${FILES[@]}"; do
            SRC="gdrive:GIS/Satellite imagery/Planet imagery/NICFI Monthly Mosaics/${YEAR}/${MONTH}/${FILENAME}"
            DEST="do-space:choco-forest-watch/NICFI Monthly Mosaics/${YEAR}/${MONTH}"

            log "Starting upload of $FILENAME ..."
            
            if rclone copy "$SRC" "$DEST" \
                --progress --transfers 16 --checkers 32 \
                --s3-upload-concurrency 8 \
                --s3-chunk-size 128M \
                --drive-pacer-min-sleep 200ms \
                --drive-pacer-burst 200; then
                log "Successfully uploaded $FILENAME"
            else
                log "ERROR: Failed to upload $FILENAME"
                exit 1
            fi
        done
    done
done

log "Migration completed successfully!" 