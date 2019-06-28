with open("containers.tmp", "w+") as f:
    string = ""

    # Generate FSP containers
    for i in range(1, 28):
        string += "  fsp{0:02d}:\n" \
                  "    image: ${{DOCKER_REGISTRY_HOST}}/${{DOCKER_REGISTRY_USER}}/${{PROJECT}}:latest\n" \
                  "    network_mode: ${{NETWORK_MODE}}\n" \
                  "    container_name: ${{CONTAINER_NAME_PREFIX}}fsp{0:02d}\n" \
                  "    depends_on:\n" \
                  "      - databaseds\n" \
                  "      - rsyslog-midcbf\n" \
                  "    environment:\n" \
                  "      - TANGO_HOST=${{TANGO_HOST}}\n" \
                  "    command: >\n" \
                  "      sh -c \"wait-for-it.sh ${{TANGO_HOST}} --timeout=30 --strict --\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_corr/{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/Fsp/FspCorr/FspCorr.py fsp-{0:02d} & true &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_pss/{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/Fsp/FspPss/FspPss.py fsp-{0:02d} & true &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_pst/{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/Fsp/FspPst/FspPst.py fsp-{0:02d} & true &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_vlbi/{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/Fsp/FspVlbi/FspVlbi.py fsp-{0:02d} & true &&\\\n" \
                  "             for j in $$(seq -w 1 16); do \\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fspSubarray/{0:02d}\_$$j &&\\\n" \
                  "             /venv/bin/python /app/csplmc/Fsp/FspSubarray/FspSubarray.py fspSubarray-{0:02d}-$$j & true; done &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp/{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/Fsp/Fsp/Fsp.py fsp-{0:02d}\"\n\n".format(i)

    # Generate CBF Subarray containers
    for i in range(1, 17):
        string += "  cbfsubarray{0:02d}:\n" \
                  "    image: ${{DOCKER_REGISTRY_HOST}}/${{DOCKER_REGISTRY_USER}}/${{PROJECT}}:latest\n" \
                  "    network_mode: ${{NETWORK_MODE}}\n" \
                  "    container_name: ${{CONTAINER_NAME_PREFIX}}cbfsubarray{0:02d}\n" \
                  "    depends_on:\n" \
                  "      - vcc\n" \
                  "      - fsp01\n" \
                  "      - fsp02\n" \
                  "      - fsp03\n" \
                  "      - fsp04\n" \
                  "      - fsp05\n" \
                  "      - fsp06\n" \
                  "      - fsp07\n" \
                  "      - fsp08\n" \
                  "      - fsp09\n" \
                  "      - fsp10\n" \
                  "      - fsp11\n" \
                  "      - fsp12\n" \
                  "      - fsp13\n" \
                  "      - fsp14\n" \
                  "      - fsp15\n" \
                  "      - fsp16\n" \
                  "      - fsp17\n" \
                  "      - fsp18\n" \
                  "      - fsp19\n" \
                  "      - fsp20\n" \
                  "      - fsp21\n" \
                  "      - fsp22\n" \
                  "      - fsp23\n" \
                  "      - fsp24\n" \
                  "      - fsp25\n" \
                  "      - fsp26\n" \
                  "      - fsp27\n" \
                  "      - databaseds\n" \
                  "      - rsyslog-midcbf\n" \
                  "    environment:\n" \
                  "      - TANGO_HOST=${{TANGO_HOST}}\n" \
                  "    command: >\n" \
                  "      sh -c \"wait-for-it.sh ${{TANGO_HOST}} --timeout=30 --strict --\n" \
                  "             tango_admin --check-device mid_csp_cbf/sw1/{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/CbfSubarray/SearchWindow/SearchWindow.py sw1-{0:02d} & true &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/sw2/{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/CbfSubarray/SearchWindow/SearchWindow.py sw2-{0:02d} & true &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/sub_elt/subarray_{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/CbfSubarray/CbfSubarray/CbfSubarray.py cbfSubarray-{0:02d}\"\n\n".format(i)

    f.write(string)
