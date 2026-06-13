#!/bin/bash
# Migration cleanup and reset script

echo "=== Cleaning up Alembic migration state ==="

# Step 1: Clean the alembic_version table
echo "Step 1: Cleaning alembic_version table..."
python3 clean_migrations.py

if [ $? -ne 0 ]; then
    echo "Failed to clean migrations. Exiting."
    exit 1
fi

# Step 2: Run all migrations
echo ""
echo "Step 2: Running all migrations..."
alembic upgrade head

if [ $? -ne 0 ]; then
    echo "Failed to run migrations. Exiting."
    exit 1
fi

echo ""
echo "=== Migration cleanup and upgrade completed successfully ==="
