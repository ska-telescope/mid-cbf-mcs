#!/usr/bin/env bash
echo "STATIC CODE ANALYSIS"
echo "===================="
echo

echo "MODULE ANALYSIS"
echo "---------------"
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/controller
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/subarray
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/vcc
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/fsp
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/commons
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/power_switch
pylint --rcfile=.pylintrc src/ska_mid_cbf_mcs/talon_lru
