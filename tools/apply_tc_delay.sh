#!/bin/bash

# Apply network delays using tc (traffic control) directly in pods

NAMESPACE="dtn-lab"

echo "Applying space communication delays using tc..."

# Apply delay on satellite pod (satellite -> lunar base: 1300ms)
SATELLITE_POD=$(kubectl -n $NAMESPACE get pods -l node=satellite -o jsonpath='{.items[0].metadata.name}')
if [ -n "$SATELLITE_POD" ]; then
    echo "Applying 1300ms delay on satellite -> lunar-base traffic"
    kubectl -n $NAMESPACE exec $SATELLITE_POD -- sh -c "
        apt-get update && apt-get install -y iproute2 2>/dev/null || true
        tc qdisc add dev eth0 root netem delay 1300ms 500ms loss 8% corrupt 3% 2>/dev/null || \
        tc qdisc change dev eth0 root netem delay 1300ms 500ms loss 8% corrupt 3% 2>/dev/null || \
        echo 'Could not apply tc rules (may need privileged mode)'
    "
fi

# Apply delay on earth station pod (earth -> satellite: 50ms)  
EARTH_POD=$(kubectl -n $NAMESPACE get pods -l node=earth-station -o jsonpath='{.items[0].metadata.name}')
if [ -n "$EARTH_POD" ]; then
    echo "Applying 50ms delay on earth -> satellite traffic"
    kubectl -n $NAMESPACE exec $EARTH_POD -- sh -c "
        apt-get update && apt-get install -y iproute2 2>/dev/null || true
        tc qdisc add dev eth0 root netem delay 50ms 10ms loss 2% 2>/dev/null || \
        tc qdisc change dev eth0 root netem delay 50ms 10ms loss 2% 2>/dev/null || \
        echo 'Could not apply tc rules (may need privileged mode)'
    "
fi

echo "Done. Note: tc rules may not work without privileged containers."