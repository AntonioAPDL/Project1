#!/bin/bash

SOURCE_DIR="/home/jaguir26/project1_ucsc_phd"
BUCKET_NAME="project1_ucsc_phd"
DEST_DIR="gs://$BUCKET_NAME/notebooks_backup"

# Exclude file pattern for extremely large files and google-cloud-sdk directory
EXCLUDE_PATTERN="(variables_50_AV.RData|variables_50_exAL.RData|variables_50_SL.RData|variables_5_exAL.RData|variables_95_exAL.RData|variables_95_SL.RData|google-cloud-sdk/.*)"

# Sync local directory to GCS, excluding extremely large files and google-cloud-sdk directory
gsutil -m rsync -r -x "$EXCLUDE_PATTERN" $SOURCE_DIR $DEST_DIR

