from num_capabilities import *

with open("mid-cbf-mcs.yml", "w+") as f:
    string = "version: \"2.2\"\n\nservices:\n"

    containers_vcc = [*map(lambda j: "vcc{:03d}".format(j), range(1, num_vcc + 1))]
    containers_fsp = [*map(lambda j: "fsp{:02d}".format(j), range(1, num_fsp + 1))]
    containers_cbf_subarray = [*map(lambda j: "cbfsubarray{:02d}".format(j), range(1, num_subarray + 1))]
    depends_on_vcc = "\n      - ".join(containers_vcc)
    depends_on_fsp = "\n      - ".join(containers_fsp)
    depends_on_cbf_subarray = "\n      - ".join(containers_cbf_subarray)

    # Generate VCC containers
    for i in range(1, num_vcc + 1):
        string += "  vcc{0:03d}:\n" \
                  "    image: ${{DOCKER_REGISTRY_HOST}}/${{DOCKER_REGISTRY_USER}}/${{PROJECT}}:latest\n" \
                  "    network_mode: ${{NETWORK_MODE}}\n" \
                  "    container_name: ${{CONTAINER_NAME_PREFIX}}vcc{0:03d}\n" \
                  "    depends_on:\n" \
                  "      - databaseds\n" \
                  "      - rsyslog\n" \
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
                  "             /venv/bin/python /app/tangods/Vcc/VccMulti/VccMulti.py vcc-{0:03d}\"\n\n".format(i)

    # Generate FSP containers
    for i in range(1, num_fsp + 1):
        string += "  fsp{0:02d}:\n" \
                  "    image: ${{DOCKER_REGISTRY_HOST}}/${{DOCKER_REGISTRY_USER}}/${{PROJECT}}:latest\n" \
                  "    network_mode: ${{NETWORK_MODE}}\n" \
                  "    container_name: ${{CONTAINER_NAME_PREFIX}}fsp{0:02d}\n" \
                  "    depends_on:\n" \
                  "      - {1}\n" \
                  "      - databaseds\n" \
                  "      - rsyslog\n" \
                  "    environment:\n" \
                  "      - TANGO_HOST=${{TANGO_HOST}}\n" \
                  "    command: >\n" \
                  "      sh -c \"wait-for-it.sh ${{TANGO_HOST}} --timeout=60 --strict --\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_corr/{0:02d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_pss/{0:02d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_pst/{0:02d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp_vlbi/{0:02d} &&\\\n" \
                  "             for j in $$(seq -w 1 16); do \\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fspCorrSubarray/{0:02d}\_$$j; done &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/fsp/{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/tangods/Fsp/FspMulti/FspMulti.py fsp-{0:02d}\"\n\n".format(i, depends_on_vcc)

    # Generate CBF Subarray containers
    for i in range(1, num_subarray + 1):
        string += "  cbfsubarray{0:02d}:\n" \
                  "    image: ${{DOCKER_REGISTRY_HOST}}/${{DOCKER_REGISTRY_USER}}/${{PROJECT}}:latest\n" \
                  "    network_mode: ${{NETWORK_MODE}}\n" \
                  "    container_name: ${{CONTAINER_NAME_PREFIX}}cbfsubarray{0:02d}\n" \
                  "    depends_on:\n" \
                  "      - {1}\n" \
                  "      - {2}\n" \
                  "      - databaseds\n" \
                  "      - rsyslog\n" \
                  "    environment:\n" \
                  "      - TANGO_HOST=${{TANGO_HOST}}\n" \
                  "    command: >\n" \
                  "      sh -c \"wait-for-it.sh ${{TANGO_HOST}} --timeout=60 --strict --\n" \
                  "             tango_admin --check-device mid_csp_cbf/sw1/{0:02d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/sw2/{0:02d} &&\\\n" \
                  "             tango_admin --check-device mid_csp_cbf/sub_elt/subarray_{0:02d} &&\\\n" \
                  "             /venv/bin/python /app/tangods/CbfSubarray/CbfSubarrayMulti/CbfSubarrayMulti.py cbfSubarray-{0:02d}\"\n\n".format(i, depends_on_vcc, depends_on_fsp)

    string += "  cbfmaster:\n" \
              "    image: ${{DOCKER_REGISTRY_HOST}}/${{DOCKER_REGISTRY_USER}}/${{PROJECT}}:latest\n" \
              "    network_mode: ${{NETWORK_MODE}}\n" \
              "    container_name: ${{CONTAINER_NAME_PREFIX}}cbfmaster\n" \
              "    depends_on:\n" \
              "      - {0}\n" \
              "      - {1}\n" \
              "      - {2}\n" \
              "      - databaseds\n" \
              "      - rsyslog\n" \
              "    environment:\n" \
              "      - TANGO_HOST=${{TANGO_HOST}}\n" \
              "    command: >\n" \
              "      sh -c \"wait-for-it.sh ${{TANGO_HOST}} --timeout=60 --strict --\n" \
              "             tango_admin --check-device mid_csp_cbf/sub_elt/master &&\\\n" \
              "             /venv/bin/python /app/tangods/CbfMaster/CbfMaster/CbfMaster.py master\"\n\n".format(depends_on_vcc, depends_on_fsp, depends_on_cbf_subarray)

    string += "  tmcspsubarrayleafnodetest:\n" \
              "    image: ${DOCKER_REGISTRY_HOST}/${DOCKER_REGISTRY_USER}/${PROJECT}:latest\n" \
              "    network_mode: ${NETWORK_MODE}\n" \
              "    container_name: ${CONTAINER_NAME_PREFIX}tmcspsubarrayleafnodetest\n" \
              "    depends_on:\n" \
              "      - cbfmaster\n" \
              "      - databaseds\n" \
              "      - rsyslog\n" \
              "    environment:\n" \
              "      - TANGO_HOST=${TANGO_HOST}\n" \
              "    command: >\n" \
              "      sh -c \"wait-for-it.sh ${TANGO_HOST} --timeout=60 --strict --\n" \
              "             tango_admin --check-device ska_mid/tm_leaf_node/csp_subarray_01 &&\\\n" \
              "             /venv/bin/python /app/tangods/TmCspSubarrayLeafNodeTest/TmCspSubarrayLeafNodeTest.py tm\"\n\n"

    string += "  tmcspsubarrayleafnodetest:\n" \
              "    image: ${DOCKER_REGISTRY_HOST}/${DOCKER_REGISTRY_USER}/${PROJECT}:latest\n" \
              "    network_mode: ${NETWORK_MODE}\n" \
              "    container_name: ${CONTAINER_NAME_PREFIX}tmcspsubarrayleafnodetest\n" \
              "    depends_on:\n" \
              "      - cbfmaster\n" \
              "      - databaseds\n" \
              "      - rsyslog\n" \
              "    environment:\n" \
              "      - TANGO_HOST=${TANGO_HOST}\n" \
              "    command: >\n" \
              "      sh -c \"wait-for-it.sh ${TANGO_HOST} --timeout=60 --strict --\n" \
              "             tango_admin --check-device ska_mid/tm_leaf_node/csp_subarray_02 &&\\\n" \
              "             /venv/bin/python /app/tangods/TmCspSubarrayLeafNodeTest/TmCspSubarrayLeafNodeTest.py tm2\"\n\n"

    string += "  rsyslog:\n" \
              "    image: jumanjiman/rsyslog\n" \
              "    network_mode: ${NETWORK_MODE}\n" \
              "    container_name: ${CONTAINER_NAME_PREFIX}rsyslog\n"

    f.write(string)
