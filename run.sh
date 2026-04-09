#!/bin/bash
# Starts the local contacts overview app.
# First run installs dependencies and builds the frontend.
# Usage: ./run.sh [--rebuild]

set -e
cd "$(dirname "$0")"

echo "Installing backend dependencies..."
pip3 install -q -r backend/requirements.txt

NEEDS_BUILD=false
if [ ! -d "frontend/dist" ]; then
  NEEDS_BUILD=true
elif [ "$1" = "--rebuild" ]; then
  NEEDS_BUILD=true
elif find frontend/src frontend/index.html frontend/package.json -newer frontend/dist/index.html 2>/dev/null | grep -q .; then
  echo "Frontend source changed — rebuilding..."
  NEEDS_BUILD=true
fi

if [ "$NEEDS_BUILD" = true ]; then
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
