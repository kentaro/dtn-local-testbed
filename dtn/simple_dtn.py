#!/usr/bin/env python3
"""
Simple DTN (Delay/Disruption Tolerant Network) Implementation
Implements basic Bundle Protocol with Store-and-Forward capability
"""

import json
import time
import socket
import threading
import queue
import os
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pickle

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class Bundle:
    """DTN Bundle - the basic unit of data transfer"""
    def __init__(self, source: str, destination: str, payload: bytes, 
                 lifetime: int = 3600, priority: int = 1):
        self.bundle_id = hashlib.sha256(
            f"{source}{destination}{time.time()}".encode()
        ).hexdigest()[:16]
        self.source = source
        self.destination = destination
        self.payload = payload
        self.creation_timestamp = time.time()
        self.lifetime = lifetime  # seconds
        self.priority = priority
        self.hop_count = 0
        self.forwarded_by = []
        
    def is_expired(self) -> bool:
        """Check if bundle has exceeded its lifetime"""
        return time.time() - self.creation_timestamp > self.lifetime
    
    def add_hop(self, node_id: str):
        """Track forwarding path"""
        self.hop_count += 1
        self.forwarded_by.append(node_id)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'bundle_id': self.bundle_id,
            'source': self.source,
            'destination': self.destination,
            'payload': self.payload.decode('utf-8', errors='replace'),
            'creation_timestamp': self.creation_timestamp,
            'lifetime': self.lifetime,
            'priority': self.priority,
            'hop_count': self.hop_count,
            'forwarded_by': self.forwarded_by
        }

class BundleStore:
    """Persistent storage for bundles (Store-and-Forward)"""
    def __init__(self, storage_path: str = "/tmp/dtn_bundles"):
        self.storage_path = storage_path
        self.bundles: Dict[str, Bundle] = {}
        self.lock = threading.Lock()
        os.makedirs(storage_path, exist_ok=True)
        self.load_bundles()
    
    def store(self, bundle: Bundle) -> bool:
        """Store bundle persistently"""
        with self.lock:
            if bundle.bundle_id in self.bundles:
                return False  # Duplicate
            
            self.bundles[bundle.bundle_id] = bundle
            # Persist to disk
            bundle_file = os.path.join(self.storage_path, f"{bundle.bundle_id}.bundle")
            try:
                with open(bundle_file, 'wb') as f:
                    pickle.dump(bundle, f)
                logger.info(f"Stored bundle {bundle.bundle_id} for {bundle.destination}")
                return True
            except Exception as e:
                logger.error(f"Failed to store bundle: {e}")
                return False
    
    def retrieve(self, bundle_id: str) -> Optional[Bundle]:
        """Retrieve a specific bundle"""
        with self.lock:
            return self.bundles.get(bundle_id)
    
    def get_bundles_for(self, destination: str) -> List[Bundle]:
        """Get all bundles for a specific destination"""
        with self.lock:
            return [b for b in self.bundles.values() 
                   if b.destination == destination and not b.is_expired()]
    
    def remove(self, bundle_id: str):
        """Remove delivered or expired bundle"""
        with self.lock:
            if bundle_id in self.bundles:
                del self.bundles[bundle_id]
                bundle_file = os.path.join(self.storage_path, f"{bundle_id}.bundle")
                if os.path.exists(bundle_file):
                    os.remove(bundle_file)
    
    def cleanup_expired(self):
        """Remove expired bundles"""
        with self.lock:
            expired = [bid for bid, b in self.bundles.items() if b.is_expired()]
            for bid in expired:
                logger.info(f"Removing expired bundle {bid}")
                self.remove(bid)
    
    def load_bundles(self):
        """Load bundles from disk on startup"""
        if not os.path.exists(self.storage_path):
            return
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.bundle'):
                try:
                    filepath = os.path.join(self.storage_path, filename)
                    with open(filepath, 'rb') as f:
                        bundle = pickle.load(f)
                        if not bundle.is_expired():
                            self.bundles[bundle.bundle_id] = bundle
                            logger.info(f"Loaded bundle {bundle.bundle_id}")
                except Exception as e:
                    logger.error(f"Failed to load bundle {filename}: {e}")

class DTNNode:
    """DTN Node with Store-and-Forward capability"""
    def __init__(self, node_id: str, host: str = '0.0.0.0', port: int = 4556):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.store = BundleStore(f"/tmp/dtn_bundles_{node_id}")
        self.neighbors: Dict[str, Tuple[str, int]] = {}
        self.running = False
        self.server_thread = None
        self.forward_queue = queue.Queue()
        self.metrics = {
            'bundles_received': 0,
            'bundles_forwarded': 0,
            'bundles_delivered': 0,
            'bundles_expired': 0
        }
        
        # Space communication delay simulation (from environment)
        self.send_delay_ms = int(os.environ.get('DTN_SEND_DELAY_MS', '0'))
        self.recv_delay_ms = int(os.environ.get('DTN_RECV_DELAY_MS', '0'))
        if self.send_delay_ms > 0:
            logger.info(f"Send delay: {self.send_delay_ms}ms")
        if self.recv_delay_ms > 0:
            logger.info(f"Receive delay: {self.recv_delay_ms}ms")
        
    def add_neighbor(self, node_id: str, host: str, port: int):
        """Add a neighboring node for routing"""
        self.neighbors[node_id] = (host, port)
        logger.info(f"Added neighbor: {node_id} at {host}:{port}")
    
    def start(self):
        """Start the DTN node"""
        self.running = True
        
        # Start server thread
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Start forwarding thread
        forward_thread = threading.Thread(target=self._forward_bundles)
        forward_thread.daemon = True
        forward_thread.start()
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_expired)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        logger.info(f"DTN Node {self.node_id} started on {self.host}:{self.port}")
    
    def stop(self):
        """Stop the DTN node"""
        self.running = False
        logger.info(f"DTN Node {self.node_id} stopped")
    
    def send_bundle(self, destination: str, payload: bytes, lifetime: int = 3600):
        """Create and send a new bundle"""
        bundle = Bundle(self.node_id, destination, payload, lifetime)
        self.store.store(bundle)
        self.forward_queue.put(bundle)
        logger.info(f"Created bundle {bundle.bundle_id} for {destination}")
        return bundle.bundle_id
    
    def _run_server(self):
        """TCP server to receive bundles"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        server_socket.settimeout(1.0)
        
        while self.running:
            try:
                client_socket, addr = server_socket.accept()
                threading.Thread(
                    target=self._handle_connection, 
                    args=(client_socket,)
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Server error: {e}")
        
        server_socket.close()
    
    def _handle_connection(self, client_socket: socket.socket):
        """Handle incoming bundle"""
        try:
            # Receive bundle size
            size_data = client_socket.recv(8)
            if not size_data:
                return
            
            bundle_size = int.from_bytes(size_data, 'big')
            
            # Receive bundle data
            bundle_data = b''
            while len(bundle_data) < bundle_size:
                chunk = client_socket.recv(min(4096, bundle_size - len(bundle_data)))
                if not chunk:
                    break
                bundle_data += chunk
            
            # Apply receive delay for space communication simulation
            if self.recv_delay_ms > 0:
                delay_s = self.recv_delay_ms / 1000.0
                logger.debug(f"Applying {self.recv_delay_ms}ms receive delay")
                time.sleep(delay_s)
            
            # Deserialize bundle
            bundle = pickle.loads(bundle_data)
            bundle.add_hop(self.node_id)
            
            self.metrics['bundles_received'] += 1
            logger.info(f"Received bundle {bundle.bundle_id} from {bundle.source}")
            
            # Check if this node is the destination
            if bundle.destination == self.node_id:
                self._deliver_bundle(bundle)
            else:
                # Store and forward
                if self.store.store(bundle):
                    self.forward_queue.put(bundle)
            
            # Send acknowledgment
            client_socket.send(b'ACK')
            
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
        finally:
            client_socket.close()
    
    def _forward_bundles(self):
        """Forward bundles to appropriate neighbors"""
        while self.running:
            try:
                # Check for bundles to forward
                bundle = self.forward_queue.get(timeout=1)
                
                if bundle.is_expired():
                    self.metrics['bundles_expired'] += 1
                    self.store.remove(bundle.bundle_id)
                    continue
                
                # Simple routing: try to forward to destination or any neighbor
                success = False
                
                # Direct delivery if neighbor
                if bundle.destination in self.neighbors:
                    host, port = self.neighbors[bundle.destination]
                    if self._send_to_node(bundle, host, port):
                        success = True
                        self.metrics['bundles_forwarded'] += 1
                
                # Otherwise, forward to any available neighbor
                if not success:
                    for neighbor_id, (host, port) in self.neighbors.items():
                        if neighbor_id not in bundle.forwarded_by:
                            if self._send_to_node(bundle, host, port):
                                success = True
                                self.metrics['bundles_forwarded'] += 1
                                break
                
                if success:
                    self.store.remove(bundle.bundle_id)
                else:
                    # Retry later
                    time.sleep(5)
                    self.forward_queue.put(bundle)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Forwarding error: {e}")
    
    def _send_to_node(self, bundle: Bundle, host: str, port: int) -> bool:
        """Send bundle to another node"""
        try:
            # Apply send delay for space communication simulation
            if self.send_delay_ms > 0:
                delay_s = self.send_delay_ms / 1000.0
                logger.debug(f"Applying {self.send_delay_ms}ms send delay")
                time.sleep(delay_s)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            
            # Serialize bundle
            bundle_data = pickle.dumps(bundle)
            
            # Send size then data
            sock.send(len(bundle_data).to_bytes(8, 'big'))
            sock.send(bundle_data)
            
            # Wait for ACK
            ack = sock.recv(3)
            sock.close()
            
            if ack == b'ACK':
                logger.info(f"Forwarded bundle {bundle.bundle_id} to {host}:{port}")
                return True
            
        except Exception as e:
            logger.debug(f"Failed to send to {host}:{port}: {e}")
        
        return False
    
    def _deliver_bundle(self, bundle: Bundle):
        """Deliver bundle to local application"""
        self.metrics['bundles_delivered'] += 1
        
        # Calculate end-to-end delay
        e2e_delay = time.time() - bundle.creation_timestamp
        
        # Save to delivery log
        delivery_log = f"/tmp/dtn_delivery_{self.node_id}.json"
        delivery_data = {
            'bundle_id': bundle.bundle_id,
            'source': bundle.source,
            'destination': bundle.destination,
            'payload': bundle.payload.decode('utf-8', errors='replace'),
            'e2e_delay': e2e_delay,
            'hop_count': bundle.hop_count,
            'path': bundle.forwarded_by,
            'delivered_at': time.time()
        }
        
        try:
            # Append to JSON log
            if os.path.exists(delivery_log):
                with open(delivery_log, 'r') as f:
                    deliveries = json.load(f)
            else:
                deliveries = []
            
            deliveries.append(delivery_data)
            
            with open(delivery_log, 'w') as f:
                json.dump(deliveries, f, indent=2)
            
            logger.info(f"DELIVERED: Bundle {bundle.bundle_id} from {bundle.source}")
            logger.info(f"  Payload: {bundle.payload.decode('utf-8', errors='replace')[:50]}")
            logger.info(f"  E2E Delay: {e2e_delay:.2f}s, Hops: {bundle.hop_count}")
            
        except Exception as e:
            logger.error(f"Failed to log delivery: {e}")
    
    def _cleanup_expired(self):
        """Periodically clean up expired bundles"""
        while self.running:
            time.sleep(60)  # Check every minute
            self.store.cleanup_expired()
    
    def get_metrics(self) -> dict:
        """Get node metrics"""
        return {
            'node_id': self.node_id,
            'stored_bundles': len(self.store.bundles),
            **self.metrics
        }

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_dtn.py <node_id> [port]")
        sys.exit(1)
    
    node_id = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4556
    
    node = DTNNode(node_id, port=port)
    node.start()
    
    # Keep running
    try:
        while True:
            time.sleep(10)
            print(f"Metrics: {node.get_metrics()}")
    except KeyboardInterrupt:
        node.stop()