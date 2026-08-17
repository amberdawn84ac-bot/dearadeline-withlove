#!/bin/bash
set -e

echo "=== Seeding Production Data ==="
echo "Step 1: Curriculum sources and standards in Postgres"
python scripts/seed_curriculum.py

echo ""
echo "Step 2: Postgres curriculum concepts + prerequisites"
python scripts/seed_knowledge_graph.py

echo ""
echo "=== Seeding Complete ==="
echo "Check /health endpoint for counts"
