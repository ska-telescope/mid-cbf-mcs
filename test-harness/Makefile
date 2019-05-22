# Use bash shell with pipefail option enabled so that the return status of a
# piped command is the value of the last (rightmost) commnand to exit with a
# non-zero status. This lets us pipe output into tee but still exit on test
# failures.
SHELL = /bin/bash
.SHELLFLAGS = -o pipefail -c

all: test

# wait for the device to be available before beginning the test
# A temporary volume is mounted at /build when 'make test' is executing.
# The following steps copy across useful output to this volume which can
# then be extracted to form the CI summary for the test procedure.
test:
# 	retry --max=10 -- tango_admin --ping-device mid_csp_cbf/master/main
	for i in $$(seq -w 1 197); \
	do \
		retry --max=10 -- tango_admin --ping-device mid_csp_cbf/vcc/$$i && \
		echo Pinging mid_csp_cbf/vcc/$$i...; \
	done
	for i in $$(seq -w 1 27); \
	do \
		retry --max=10 -- tango_admin --ping-device mid_csp_cbf/fsp/$$i && \
		echo Pinging mid_csp_cbf/fsp/$$i...; \
	done
	for i in $$(seq -w 1 16); \
	do \
		retry --max=10 -- tango_admin --ping-device mid_csp_cbf/cbfSubarray/$$i && \
		echo Pinging mid_csp_cbf/cbfSubarray/$$i...; \
	done
	cd /app/csplmc/CbfMaster && python setup.py test | tee setup_py_test.stdout
	cd /app && ./code-analysis.sh | tee code_analysis.stdout
	if [ -d /build ]; then \
		mv /app/csplmc/CbfMaster/setup_py_test.stdout /build/cbf_master_setup_test.stdout; \
		mv /app/csplmc/CbfMaster/htmlcov /build/cbf_master_htmlcov; \
		mv /app/csplmc/CbfMaster/coverage.xml /build/cbf_master_coverage.xml; \
		mv /app/code_analysis.stdout /build/cbf_code_analysis.stdout; \
	fi;

.PHONY: all test
