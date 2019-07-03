with open("mid-cbf-mcs.yml", "w+") as f:
    string = "version: \"2.2\"\n\nservices:\n"

    containers_vcc = [*map(lambda j: "vcc{:03d}".format(j), range(1, 198))]
    containers_fsp = [*map(lambda j: "fsp{:02d}".format(j), range(1, 28))]
    containers_cbf_subarray = [*map(lambda j: "cbfsubarray{:02d}".format(j), range(1, 17))]
    depends_on_vcc = "\n      - ".join(containers_vcc)
    depends_on_fsp = "\n      - ".join(containers_fsp)
    depends_on_cbf_subarray = "\n      - ".join(containers_cbf_subarray)

    # Generate VCC containers
    for i in range(1, 198):
        string += "  vcc{0:03d}:\n" \
                  "    image: ${{DOCKER_REGISTRY_HOST}}/${{DOCKER_REGISTRY_USER}}/${{PROJECT}}:latest\n" \
                  "    network_mode: ${{NETWORK_MODE}}\n" \
                  "    container_name: ${{CONTAINER_NAME_PREFIX}}vcc{0:03d}\n" \
                  "    depends_on:\n" \
                  "      - databaseds\n" \
                  "      - rsyslog-midcbf\n" \
                  "    environment:\n" \
                  "      - TANGO_HOST=${{TANGO_HOST}}\n" \
                  "    command: >\n" \
                  "      sh -c \"wait-for-it.sh ${{TANGO_HOST}} --timeout=60 --strict --\n" \
                  "             tango_admin --check-device mid_csp_cbf/vcc_band12/{0:03d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/vcc_band3/{0:03d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/vcc_band4/{0:03d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/vcc_band5/{0:03d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/vcc_sw1/{0:03d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/vcc_sw2/{0:03d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/vcc/{0:03d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/Vcc/VccMulti/VccMulti.py vcc-{0:03d}\"\n\n".format(i)

    # Generate FSP containers
    for i in range(1, 28):
        string += "  fsp{0:02d}:\n" \
                  "    image: ${{DOCKER_REGISTRY_HOST}}/${{DOCKER_REGISTRY_USER}}/${{PROJECT}}:latest\n" \
                  "    network_mode: ${{NETWORK_MODE}}\n" \
                  "    container_name: ${{CONTAINER_NAME_PREFIX}}fsp{0:02d}\n" \
                  "    depends_on:\n" \
                  "      - {1}\n" \
                  "      - databaseds\n" \
                  "      - rsyslog-midcbf\n" \
                  "    environment:\n" \
                  "      - TANGO_HOST=${{TANGO_HOST}}\n" \
                  "    command: >\n" \
                  "      sh -c \"wait-for-it.sh ${{TANGO_HOST}} --timeout=60 --strict --\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_corr/{0:02d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_pss/{0:02d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_pst/{0:02d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_vlbi/{0:02d} &&\\\n" \
                  "             for j in $$(seq -w 1 16); do \\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fspSubarray/{0:02d}\_$$j; done &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp/{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/Fsp/FspMulti/FspMulti.py fsp-{0:02d}\"\n\n".format(i, depends_on_vcc)

    # Generate CBF Subarray containers
    for i in range(1, 17):
        string += "  cbfsubarray{0:02d}:\n" \
                  "    image: ${{DOCKER_REGISTRY_HOST}}/${{DOCKER_REGISTRY_USER}}/${{PROJECT}}:latest\n" \
                  "    network_mode: ${{NETWORK_MODE}}\n" \
                  "    container_name: ${{CONTAINER_NAME_PREFIX}}cbfsubarray{0:02d}\n" \
                  "    depends_on:\n" \
                  "      - {1}\n" \
                  "      - {2}\n" \
                  "      - databaseds\n" \
                  "      - rsyslog-midcbf\n" \
                  "    environment:\n" \
                  "      - TANGO_HOST=${{TANGO_HOST}}\n" \
                  "    command: >\n" \
                  "      sh -c \"wait-for-it.sh ${{TANGO_HOST}} --timeout=60 --strict --\n" \
                  "             tango_admin --check-device mid_csp_cbf/sw1/{0:02d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/sw2/{0:02d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/sub_elt/subarray_{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/csplmc/CbfSubarray/CbfSubarrayMulti/CbfSubarrayMulti.py cbfSubarray-{0:02d}\"\n\n".format(i, depends_on_vcc, depends_on_fsp)

    string += "  cbfmaster:\n" \
              "    image: ${{DOCKER_REGISTRY_HOST}}/${{DOCKER_REGISTRY_USER}}/${{PROJECT}}:latest\n" \
              "    network_mode: ${{NETWORK_MODE}}\n" \
              "    container_name: ${{CONTAINER_NAME_PREFIX}}cbfmaster\n" \
              "    depends_on:\n" \
              "      - {0}\n" \
              "      - {1}\n" \
              "      - {2}\n" \
              "      - databaseds\n" \
              "      - rsyslog-midcbf\n" \
              "    environment:\n" \
              "      - TANGO_HOST=${{TANGO_HOST}}\n" \
              "    command: >\n" \
              "      sh -c \"wait-for-it.sh ${{TANGO_HOST}} --timeout=60 --strict --\n" \
              "             tango_admin --check-device mid_csp_cbf/sub_elt/master &&\\\n" \
              "             /venv/bin/python /app/csplmc/CbfMaster/CbfMaster/CbfMaster.py master\"\n\n".format(depends_on_vcc, depends_on_fsp, depends_on_cbf_subarray)

    string += "  tmtelstatetest:\n" \
              "    image: ${DOCKER_REGISTRY_HOST}/${DOCKER_REGISTRY_USER}/${PROJECT}:latest\n" \
              "    network_mode: ${NETWORK_MODE}\n" \
              "    container_name: ${CONTAINER_NAME_PREFIX}tmtelstatetest\n" \
              "    depends_on:\n" \
              "      - cbfmaster\n" \
              "      - databaseds\n" \
              "      - rsyslog-midcbf\n" \
              "    environment:\n" \
              "      - TANGO_HOST=${TANGO_HOST}\n" \
              "    command: >\n" \
              "      sh -c \"wait-for-it.sh ${TANGO_HOST} --timeout=60 --strict --\n" \
              "             tango_admin --check-device ska1_mid/tm/telmodel &&\\\n" \
              "             /venv/bin/python /app/csplmc/TmTelstateTest/TmTelstateTest.py tm\"\n\n"

    string += "  rsyslog-midcbf:\n" \
              "    image: jumanjiman/rsyslog\n" \
              "    network_mode: ${NETWORK_MODE}\n" \
              "    container_name: ${CONTAINER_NAME_PREFIX}rsyslog-midcbf\n"

    f.write(string)
