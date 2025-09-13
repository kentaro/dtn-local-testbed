#!/bin/bash

# DTN Node Launcher Script
# Configures and starts a DTN node based on environment variables

NODE_ID=${DTN_NODE_ID:-"node"}
NODE_TYPE=${DTN_NODE_TYPE:-"relay"}
PORT=${DTN_PORT:-4556}
NEIGHBORS=${DTN_NEIGHBORS:-""}

echo "========================================="
echo "Starting DTN Node"
echo "========================================="
echo "Node ID: $NODE_ID"
echo "Node Type: $NODE_TYPE"
echo "Port: $PORT"
echo "Neighbors: $NEIGHBORS"
echo "========================================="

# Create Python script to configure and run the node
cat > /tmp/run_node.py << 'EOF'
import os
import sys
import time
import threading
import random
sys.path.append('/dtn')
from simple_dtn import DTNNode

# Get configuration from environment
node_id = os.environ.get('DTN_NODE_ID', 'node')
node_type = os.environ.get('DTN_NODE_TYPE', 'relay')
port = int(os.environ.get('DTN_PORT', '4556'))
neighbors = os.environ.get('DTN_NEIGHBORS', '')

# Create node
node = DTNNode(node_id, port=port)

# Parse and add neighbors
# Format: "id1:host1:port1,id2:host2:port2"
if neighbors:
    for neighbor in neighbors.split(','):
        if neighbor:
            parts = neighbor.split(':')
            if len(parts) == 3:
                nid, nhost, nport = parts
                node.add_neighbor(nid, nhost, int(nport))
                print(f"Added neighbor: {nid} at {nhost}:{nport}")

# Start the node
node.start()

# Node-specific behavior
if node_type == 'earth':
    print("Earth Station: Generating telemetry bundles")
    def send_telemetry():
        seq = 0
        while True:
            time.sleep(random.randint(5, 15))  # Random interval
            seq += 1
            
            # Create telemetry data
            telemetry_types = ['ORBIT_ADJUST', 'SCIENCE_DATA', 'HEALTH_CHECK', 'TIME_SYNC']
            ttype = random.choice(telemetry_types)
            
            payload = f"""{{
                "seq": {seq},
                "type": "{ttype}",
                "timestamp": {time.time()},
                "data": "Telemetry data packet {seq}",
                "source": "{node_id}"
            }}""".encode()
            
            # Send to lunar base via satellite
            bundle_id = node.send_bundle('lunar-base', payload, lifetime=7200)
            print(f"[EARTH] Sent telemetry #{seq} (type: {ttype}), bundle: {bundle_id}")
    
    threading.Thread(target=send_telemetry, daemon=True).start()

elif node_type == 'lunar':
    print("Lunar Base: Ready to receive telemetry")
    # Lunar base just receives and logs
    
elif node_type == 'satellite':
    print("LEO Satellite: Relay mode active")
    # Satellite relays bundles between Earth and Moon

# Periodic metrics reporting
def report_metrics():
    while True:
        time.sleep(30)
        metrics = node.get_metrics()
        print(f"[METRICS] {metrics}")

threading.Thread(target=report_metrics, daemon=True).start()

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    node.stop()
    print(f"Node {node_id} stopped")
EOF

# Run the node
python3 /tmp/run_node.py