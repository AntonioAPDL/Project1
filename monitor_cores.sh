#!/bin/bash

echo "=============================================="
echo "       CPU Core Usage on Jerez & Muscat"
echo "=============================================="

# Function to display CPU core usage
check_cpu_cores() {
    echo "----------------------------------------------"
    echo " Server: $1"
    echo "----------------------------------------------"
    ssh "$1" "ps -eo psr,pid,%cpu,cmd --sort=psr | grep -E 'R|Rscript|python|mpirun' | tail -n 15"
    echo ""
}

# Check CPU usage on Jerez
check_cpu_cores "jaguir26@jerez.be.ucsc.edu"

# Check CPU usage on Muscat
check_cpu_cores "jaguir26@muscat.be.ucsc.edu"

echo "=============================================="
echo "  Done! You can now analyze which cores are active."
echo "=============================================="

