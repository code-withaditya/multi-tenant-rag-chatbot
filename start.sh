#!/bin/bash

# 1. Start the FastAPI backend in the background on port 8000
echo "Starting FastAPI backend..."
uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# 2. Wait a brief moment for the backend to initialize
sleep 3

# 3. Start the Streamlit frontend in the foreground on Hugging Face's required port (7860)
echo "Starting Streamlit frontend..."
streamlit run frontend.py --server.port 7860 --server.address 0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false