#!/bin/bash

echo "Running connection test in container..."
echo "TODO: write test script"
docker exec python_postgres_demo python --version
docker exec postgres_bigm_demo pg_isready
