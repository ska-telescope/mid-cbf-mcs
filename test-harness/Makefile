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
	echo Pinging mid_csp_cbf/sub_elt/master...;
	retry --max=10 -- tango_admin --ping-device mid_csp_cbf/sub_elt/master
	echo Pinging ska_mid/tm_leaf_node/csp_subarray_01...;
	retry --max=10 -- tango_admin --ping-device ska_mid/tm_leaf_node/csp_subarray_01
	for i in $$(seq -w 1 4); do \
		echo Pinging mid_csp_cbf/vcc/$$i...; \
		retry --max=10 -- tango_admin --ping-device mid_csp_cbf/vcc/00$$i; \
        done 		
	for i in $$(seq -w 1 4); do \
		echo Pinging mid_csp_cbf/fsp/$$i...; \
		retry --max=10 -- tango_admin --ping-device mid_csp_cbf/fsp/0$$i;  \
	done
	for i in $$(seq -w 1 2); \
	do \
		echo Pinging mid_csp_cbf/sub_elt/subarray_$$i...; \
		retry --max=10 -- tango_admin --ping-device mid_csp_cbf/sub_elt/subarray_0$$i;  \
	done
	cd /app && pytest $(if $(findstring all,$(MARK)),, -m '$(MARK)') | tee setup_py_test.stdout
	cd /app && ./code-analysis.sh | tee code_analysis.stdout
	mkdir -p build/reports && \
	if [ -d build ]; then \
		mv /app/setup_py_test.stdout ./build/setup_test.stdout; \
		mv /app/htmlcov ./build/htmlcov; \
		mv /app/coverage.xml ./build/reports/code-coverage.xml; \
		mv /app/code_analysis.stdout ./build/cbf_code_analysis.stdout; \
		cp /app/build/reports/unit-tests.xml ./build/reports; \
	fi;
.PHONY: all test
