#!/usr/bin/env bash
echo "STATIC CODE ANALYSIS"
echo "===================="
echo

echo "MODULE ANALYSIS"
echo "---------------"
pylint --rcfile=.pylintrc csplmc/CspMaster/CspMaster

echo "TESTS ANALYSIS"
echo "--------------"
pylint --rcfile=.pylintrc csplmc/CspMaster/test
