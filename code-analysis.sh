#!/usr/bin/env bash
echo "STATIC CODE ANALYSIS"
echo "===================="
echo

echo "MODULE ANALYSIS"
echo "---------------"
pylint --rcfile=.pylintrc tangods/CbfMaster/CbfMaster
pylint --rcfile=.pylintrc tangods/CbfSubarray/CbfSubarray
pylint --rcfile=.pylintrc tangods/Vcc/Vcc
pylint --rcfile=.pylintrc tangods/Fsp/Fsp
pylint --rcfile=.pylintrc tangods/commons

#echo "TESTS ANALYSIS"
#echo "--------------"
#pylint --rcfile=.pylintrc tangods/CspMaster/test
