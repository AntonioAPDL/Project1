#!/bin/bash

# Define servers
servers=("jaguir26@muscat.be.ucsc.edu" "jaguir26@jerez.be.ucsc.edu")

# Print header
echo "=============================================="
echo "       Server Resource Monitoring"
echo "=============================================="

# Function to fetch resource usage from a server
fetch_usage() {
    local server=$1
    echo "Checking resource usage on $server..."
    ssh "$server" <<'EOF'
        echo "----------------------------------------------"
        echo "Server: $(hostname)"
        echo "----------------------------------------------"
        
        # CPU Usage
        echo "CPU Usage (Top 5 processes by CPU usage):"
        ps -eo pid,comm,%cpu --sort=-%cpu | head -n 6
        
        # Memory Usage
        echo ""
        echo "Memory Usage (Top 5 processes by memory usage):"
        ps -eo pid,comm,%mem --sort=-%mem | head -n 6
        
        # Overall CPU & Memory Stats
        echo ""
        echo "Overall CPU and Memory Stats:"
        top -b -n 1 | head -n 10
        
        echo "----------------------------------------------"
EOF
}

# Loop through each server and fetch usage
for server in "${servers[@]}"; do
    fetch_usage "$server"
    echo ""
done

