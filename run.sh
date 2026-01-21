#!/bin/bash
# Kill any existing Uvicorn process on port 8001
fuser -k 8001/tcp

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8001

