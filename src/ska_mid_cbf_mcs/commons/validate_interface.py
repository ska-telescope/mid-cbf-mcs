import json

CSP_CONFIGURE_PREFIX = "https://schema.skao.int/ska-csp-configure/"
CSP_CONFIGURESCAN_PREFIX = "https://schema.skao.int/ska-csp-configurescan/"
CSP_DELAYMODEL_PREFIX = "https://schema.skao.int/ska-csp-delaymodel/"
CSP_SCAN_PREFIX = "https://schema.skao.int/ska-csp-scan/"
CSP_INITSYSPARAM_PREFIX = "https://schema.skao.int/ska-mid-cbf-initsysparam/"

CSP_CONFIGURESCAN_VER3_0 = CSP_CONFIGURESCAN_PREFIX + "3.0"
CSP_CONFIGURESCAN_VER4_1 = CSP_CONFIGURESCAN_PREFIX + "4.1"
CSP_CONFIGURESCAN_VER2_5 = CSP_CONFIGURE_PREFIX + "2.5"

CSP_DELAYMODEL_VER3_0 = CSP_DELAYMODEL_PREFIX + "3.0"

CSP_SCAN_VER2_3 = CSP_SCAN_PREFIX + "2.3"

CSP_INITSYSPARAM_VER1_0 = CSP_INITSYSPARAM_PREFIX + "1.0"

# List of supported interfaces. Dependent on which stories have been merged into main

CSP_CONFIGURESCAN_VERSIONS = [
    CSP_CONFIGURESCAN_VER3_0,  # If only CIP-2504 has been merged
    #    CSP_CONFIGURESCAN_VER4_1,   # If CIP-2253 and CIP-2616 have been merged
    # CSP_CONFIGURESCAN_VER2_5,  # If none of the above have been merged
]
CSP_DELAYMODEL_VERSIONS = [CSP_DELAYMODEL_VER3_0]
CSP_SCAN_VERSIONS = [CSP_SCAN_VER2_3]
CSP_INITSYSPARAM_VERSIONS = [CSP_INITSYSPARAM_VER1_0]


supported_interfaces = {
    'configurescan': CSP_CONFIGURESCAN_VERSIONS,
    'delaymodel': CSP_DELAYMODEL_VERSIONS,
    'scan': CSP_SCAN_VERSIONS,
    'initsysparam': CSP_INITSYSPARAM_VERSIONS,
}


def validate_interface(argin: str) -> tuple[bool, str]:
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

    # Check supported interface
    if not any(
        input["interface"] in val for val in supported_interfaces.values()
    ):
        return [False, "The command interface is not supported"]

    # Return pass
    return [True, ""]
