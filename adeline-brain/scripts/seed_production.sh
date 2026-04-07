#!/bin/bash
set -e

echo "=== Seeding Production Data ==="
echo "Step 1: Curriculum (Hippocampus + Neo4j OAS standards)"
python scripts/seed_curriculum.py

echo ""
echo "Step 2: Knowledge Graph (Neo4j concepts + prerequisites)"
python scripts/seed_knowledge_graph.py

echo ""
echo "=== Seeding Complete ==="
echo "Check /health endpoint for counts"
