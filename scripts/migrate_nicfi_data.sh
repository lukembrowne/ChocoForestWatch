#!/bin/bash

# Script to migrate NICFI Monthly Mosaics from Google Drive to DigitalOcean Spaces
# Usage: ./migrate_nicfi_data.sh
# Requirements: rclone, tmux

set -e  # Exit on error

# Start a new tmux session if not already in one
# if [ -z "$TMUX" ]; then
#     tmux new-session -d -s migrate
#     tmux attach-session -t migrate
# fi

# Define years and months
# YEARS=("2022")
# MONTHS=("01" "02" "03" "04" "05" "06" "07" "08" "09" "10" "11" "12")

YEARS=("2023")
MONTHS=("01")


# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}


# Main migration loop with copy
for YEAR in "${YEARS[@]}"; do
    for MONTH in "${MONTHS[@]}"; do
        
            SRC="gdrive:GIS/Satellite imagery/Planet imagery/NICFI Monthly Mosaics/${YEAR}/${MONTH}"
            DEST="do-space:choco-forest-watch/NICFI Monthly Mosaics/${YEAR}/${MONTH}"

            log "Starting copy of $SRC to $DEST ..."
            
            if rclone copy "$SRC" "$DEST" \
                --ignore-existing \
                --progress --transfers 16 --checkers 32 \
                --s3-upload-concurrency 8 \
                --s3-chunk-size 128M \
                --drive-pacer-min-sleep 200ms \
                --drive-pacer-burst 200; then
                log "Successfully synced $SRC to $DEST"
            else
                log "ERROR: Failed to sync $SRC to $DEST"
                exit 1
            fi
    done
done


log "Migration completed successfully!" 