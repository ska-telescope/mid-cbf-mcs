import json

# from ska_telmodel.csp.version import (
#     CSP_CONFIG_PREFIX,
#     CSP_CONFIGSCAN_PREFIX,
#     CSP_MID_DELAYMODEL_PREFIX,
#     CSP_SCAN_PREFIX,
# )

CSP_CONFIG_PREFIX = "https://schema.skao.int/ska-csp-configure/"
CSP_CONFIGSCAN_PREFIX = "https://schema.skao.int/ska-csp-configurescan/"
CSP_MID_DELAYMODEL_PREFIX = "https://schema.skao.int/ska-mid-csp-delaymodel/"
CSP_SCAN_PREFIX = "https://schema.skao.int/ska-csp-scan/"

CBF_INITSYSPARAM_PREFIX = "https://schema.skao.int/ska-mid-cbf-initsysparam/"

CSP_CONFIGSCAN_VER3_0 = CSP_CONFIGSCAN_PREFIX + "3.0"
CSP_CONFIGSCAN_VER4_1 = CSP_CONFIGSCAN_PREFIX + "4.1"
CSP_CONFIGSCAN_VER2_5 = CSP_CONFIG_PREFIX + "2.5"

CSP_MID_DELAYMODEL_VER3_0 = CSP_MID_DELAYMODEL_PREFIX + "3.0"

CSP_SCAN_VER2_2 = CSP_SCAN_PREFIX + "2.2"
CSP_SCAN_VER2_3 = CSP_SCAN_PREFIX + "2.3"

CBF_INITSYSPARAM_VER1_0 = CBF_INITSYSPARAM_PREFIX + "1.0"


CSP_CONFIGSCAN_VERSIONS = [
    CSP_CONFIGSCAN_VER3_0,
    # CSP_CONFIGSCAN_VER4_1,
    # CSP_CONFIGSCAN_VER2_5,
]
CSP_MID_DELAYMODEL_VERSIONS = [CSP_MID_DELAYMODEL_VER3_0]
CSP_SCAN_VERSIONS = [
    CSP_SCAN_VER2_2,
    CSP_SCAN_VER2_3,
]
CBF_INITSYSPARAM_VERSIONS = [CBF_INITSYSPARAM_VER1_0]


supported_interfaces = {
    "configure": CSP_CONFIGSCAN_VERSIONS,
    "configurescan": CSP_CONFIGSCAN_VERSIONS,
    "delaymodel": CSP_MID_DELAYMODEL_VERSIONS,
    "scan": CSP_SCAN_VERSIONS,
    "initsysparam": CBF_INITSYSPARAM_VERSIONS,
}


def validate_interface(argin: str, command: str) -> tuple[bool, str]:
    # Check valid JSON
    try:
        input = json.loads(argin)
    except json.JSONDecodeError:
        return [False, "The command parameters could not be parsed"]

    # Check interface existence
    if "interface" not in input:
        return [
            False,
            "The command is missing the required interface parameter",
        ]

    # Check interface value type
    if type(input["interface"]) is not str:
        return [
            False,
            "The value retrieved from the interface key is not a string",
        ]

    # Check supported interfaces for command
    if input["interface"] not in supported_interfaces[command]:
        return [
            False,
            f"Interface '{input['interface']}' not supported for command '{command}'",
        ]

    # Return pass
    return [True, ""]
