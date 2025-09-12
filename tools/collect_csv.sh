#!/bin/bash

set -e

NAMESPACE="dtn-lab"
POD_NAME=$(kubectl -n $NAMESPACE get pods -l node=lunar-base -o jsonpath='{.items[0].metadata.name}')
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOCAL_DIR="results"

if [ -z "$POD_NAME" ]; then
    echo "Error: Lunar base pod not found"
    exit 1
fi

echo "Collecting telemetry data from lunar base pod: $POD_NAME"

# Create results directory if it doesn't exist
mkdir -p $LOCAL_DIR

# Copy CSV file from pod
kubectl -n $NAMESPACE cp $POD_NAME:/metrics/delivery_metrics.csv $LOCAL_DIR/delivery_metrics_${TIMESTAMP}.csv

# Also create a symlink to latest
ln -sf delivery_metrics_${TIMESTAMP}.csv $LOCAL_DIR/latest_metrics.csv

echo "Telemetry data saved to: $LOCAL_DIR/delivery_metrics_${TIMESTAMP}.csv"
echo "Symlink created: $LOCAL_DIR/latest_metrics.csv"

# Display preview
echo ""
echo "Preview of collected telemetry data from lunar base:"
head -n 5 $LOCAL_DIR/latest_metrics.csv

# Count total records
TOTAL=$(tail -n +2 $LOCAL_DIR/latest_metrics.csv | wc -l)
echo ""
echo "Total telemetry packets received at lunar base: $TOTAL"