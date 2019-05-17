#!/usr/bin/env bash
echo "STATIC CODE ANALYSIS"
echo "===================="
echo

echo "MODULE ANALYSIS"
echo "---------------"
pylint --rcfile=.pylintrc csplmc/CbfMaster/CbfMaster
pylint --rcfile=.pylintrc csplmc/CbfSubarray/CbfSubarray
pylint --rcfile=.pylintrc csplmc/Vcc/Vcc
pylint --rcfile=.pylintrc csplmc/Fsp/Fsp
pylint --rcfile=.pylintrc csplmc/commons

#echo "TESTS ANALYSIS"
#echo "--------------"
#pylint --rcfile=.pylintrc csplmc/CspMaster/test
