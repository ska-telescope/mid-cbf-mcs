#!/usr/bin/env bash
echo "STATIC CODE ANALYSIS"
echo "===================="
echo

echo "MODULE ANALYSIS"
echo "---------------"
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/controller
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/CbfSubarray/CbfSubarray
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/vcc
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/Fsp/Fsp
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/commons
