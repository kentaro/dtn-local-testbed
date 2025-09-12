.PHONY: up down apply chaos delay partition bench fetch-csv plot clean

# Kind cluster management
up:
	kind create cluster --config kind-config.yaml --name dtn-lab
	kubectl cluster-info --context kind-dtn-lab

down:
	kind delete cluster --name dtn-lab

# DTN7 deployment
apply:
	kubectl apply -k .
	@echo "Waiting for Space DTN nodes to be ready..."
	kubectl -n dtn-lab wait --for=condition=ready pod -l app=dtn7 --timeout=60s

# Chaos Mesh installation
chaos:
	helm repo add chaos-mesh https://charts.chaos-mesh.org
	helm repo update
	kubectl apply -f manifests/20-chaos-namespace.yaml
	helm install chaos-mesh chaos-mesh/chaos-mesh \
		--namespace=chaos-mesh \
		--version 2.6.3 \
		--values manifests/21-chaos-values.yaml \
		--wait

# Network chaos scenarios
delay:
	kubectl apply -f manifests/30-space-comm-delay.yaml
	@echo "Applied: 1.3s light speed delay + 2% cosmic radiation packet loss on satellite->lunar traffic"

partition:
	kubectl apply -f manifests/31-earth-obstruction.yaml
	@echo "Applied: Earth obstruction between satellite and lunar base for 45 minutes"

# Benchmark execution
bench:
	kubectl delete job -n dtn-lab telemetry-burst-test --ignore-not-found=true
	kubectl apply -f manifests/40-earth-telemetry-uplink.yaml
	@echo "Telemetry burst test started. Monitoring test execution..."
	kubectl -n dtn-lab wait --for=condition=complete job/telemetry-burst-test --timeout=300s || true
	@echo "Test completed. Check logs:"
	@echo "  kubectl -n dtn-lab logs job/telemetry-burst-test"

# CSV collection and visualization
fetch-csv:
	@echo "Fetching telemetry data from Lunar Base..."
	./tools/collect_csv.sh

plot:
	@echo "Generating plots from CSV data..."
	python3 tools/plot.py

# Cleanup
clean:
	kind delete cluster --name dtn-lab
	@echo "Cluster deleted successfully"

# Helper commands
logs-earth:
	kubectl -n dtn-lab logs deploy/earth-station -f

logs-sat:
	kubectl -n dtn-lab logs deploy/leo-satellite -f

logs-lunar:
	kubectl -n dtn-lab logs deploy/lunar-base -f

status:
	kubectl -n dtn-lab get pods,svc,jobs
	kubectl get networkchaos -A