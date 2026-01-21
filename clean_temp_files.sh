#!/bin/bash

echo "----- System Health Before Cleanup -----"
echo "Memory and Swap Usage:"
free -h

echo "Disk Usage:"
df -h

echo "Top Memory-Consuming Processes:"
ps aux --sort=-%mem | head -n 10

echo "Top CPU-Consuming Processes:"
ps aux --sort=-%cpu | head -n 10

echo "Cleaning Temporary Files in /tmp and Cache..."
find /tmp -type f -mtime +1 -exec rm -f {} \;  # Delete files older than 1 day in /tmp
find ~/.cache -type f -mtime +1 -exec rm -f {} \;  # Delete files older than 1 day in cache

echo "Restarting Stuck Jupyter Notebooks..."
pkill -9 -f jupyter-lab  # Kill Jupyter-related processes

echo "----- System Health After Cleanup -----"
echo "Memory and Swap Usage:"
free -h

echo "Disk Usage:"
df -h

