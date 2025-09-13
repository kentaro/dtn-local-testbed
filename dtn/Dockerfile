FROM python:3.11-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create DTN directory
WORKDIR /dtn

# Copy DTN implementation
COPY simple_dtn.py /dtn/
COPY node_launcher.sh /dtn/

# Make scripts executable
RUN chmod +x /dtn/simple_dtn.py /dtn/node_launcher.sh

# DTN Bundle Protocol port
EXPOSE 4556

# Metrics/API port
EXPOSE 8080

# Default command
CMD ["/dtn/node_launcher.sh"]