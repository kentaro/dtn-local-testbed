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

# Check if the delivery log exists
kubectl -n $NAMESPACE exec $POD_NAME -- ls /tmp/dtn_delivery_lunar-base.json 2>/dev/null
if [ $? -eq 0 ]; then
    # Copy delivery log from pod
    kubectl -n $NAMESPACE cp $POD_NAME:/tmp/dtn_delivery_lunar-base.json $LOCAL_DIR/delivery_log_${TIMESTAMP}.json
    
    # Convert JSON to CSV for analysis
    cat > /tmp/convert_to_csv.py << 'EOF'
import json
import csv
import sys

with open(sys.argv[1], 'r') as f:
    deliveries = json.load(f)

with open(sys.argv[2], 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['bundle_id', 'source', 'e2e_delay', 'hop_count', 'delivered_at'])
    
    for d in deliveries:
        writer.writerow([
            d['bundle_id'],
            d['source'],
            d['e2e_delay'],
            d['hop_count'],
            d['delivered_at']
        ])
EOF

    python3 /tmp/convert_to_csv.py $LOCAL_DIR/delivery_log_${TIMESTAMP}.json $LOCAL_DIR/delivery_metrics_${TIMESTAMP}.csv
    
    # Create symlink to latest
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
else
    echo "No delivery log found yet. The DTN nodes may still be initializing."
    echo "Wait a few minutes and try again."
fi