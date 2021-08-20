#!/usr/bin/env bash
echo "STATIC CODE ANALYSIS"
echo "===================="
echo

echo "MODULE ANALYSIS"
echo "---------------"
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/CbfMaster/CbfMaster
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/CbfSubarray/CbfSubarray
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/Vcc/Vcc
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/Fsp/Fsp
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/commons

#echo "TESTS ANALYSIS"
#echo "--------------"
#pylint --rcfile=.pylintrc tangods/CspMaster/test
