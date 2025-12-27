#!/bin/bash
# Script pour exécuter les tests avec coverage

echo "=== Exécution des tests RFXCOM ==="
echo ""

# Tests qui fonctionnent sans dépendances
python3 -m pytest tests/test_coordinator_functions.py tests/test_const.py -v --cov=custom_components/rfxcom/const --cov-report=term-missing --cov-report=html

echo ""
echo "=== Rapport de couverture généré dans htmlcov/index.html ==="

