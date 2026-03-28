#!/bin/bash
# Starts the local contacts overview app.
# First run installs dependencies and builds the frontend.
# Usage: ./run.sh [--rebuild]

set -e
cd "$(dirname "$0")"

echo "Installing backend dependencies..."
pip3 install -q -r backend/requirements.txt

if [ ! -d "frontend/dist" ] || [ "$1" = "--rebuild" ]; then
  echo "Building frontend..."
  cd frontend
  npm install --silent
  npm run build
  cd ..
fi

echo ""
echo "Starting server → http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
