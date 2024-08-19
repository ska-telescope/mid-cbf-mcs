import json

CSP_CONFIG_PREFIX = "https://schema.skao.int/ska-csp-configure/"
CSP_DELAYMODEL_PREFIX = "https://schema.skao.int/ska-csp-delaymodel/"
CSP_SCAN_PREFIX = "https://schema.skao.int/ska-csp-scan/"
CSP_INITSYSPARAM_PREFIX = "https://schema.skao.int/ska-mid-cbf-initsysparam/"
CSP_ASSIGNRESOURCES_PREFIX = "https://schema.skao.int/ska-csp-assignresources/"
CSP_ENDSCAN_PREFIX = "https://schema.skao.int/ska-csp-endscan/"
CSP_RELEASERESOURCES_PREFIX = (
    "https://schema.skao.int/ska-csp-releaseresources/"
)

CSP_CONFIG_VER3_0 = CSP_CONFIG_PREFIX + "3.0"
CSP_CONFIG_VER4_1 = CSP_CONFIG_PREFIX + "4.1"
CSP_CONFIG_VER2_5 = CSP_CONFIG_PREFIX + "2.5"

CSP_DELAYMODEL_VER3_0 = CSP_DELAYMODEL_PREFIX + "3.0"

CSP_SCAN_VER2_3 = CSP_SCAN_PREFIX + "2.3"

CSP_INITSYSPARAM_VER1_0 = CSP_INITSYSPARAM_PREFIX + "1.0"

CSP_ASSIGNRESOURCES_VER3_0 = CSP_ASSIGNRESOURCES_PREFIX + "3.0"

CSP_ENDSCAN_VER2_3 = CSP_ENDSCAN_PREFIX + "2.3"

CSP_RELEASERESOURCES_VER3_0 = CSP_RELEASERESOURCES_PREFIX + "3.0"

# List of supported interfaces

CSP_CONFIG_VERSIONS = [CSP_CONFIG_VER2_5, CSP_CONFIG_VER3_0, CSP_CONFIG_VER4_1]
CSP_DELAYMODEL_VERSIONS = [CSP_DELAYMODEL_VER3_0]
CSP_SCAN_VERSIONS = [CSP_SCAN_VER2_3]
CSP_INITSYSPARAM_VERSIONS = [CSP_INITSYSPARAM_VER1_0]


# Dependent on which stories have been merged into main
SUPPORTED_INTERFACES = [
    CSP_CONFIG_VER3_0,  # If only CIP-2504 has been merged
    # CSP_CONFIG_VER4_1,  # If CIP-2253 and CIP-2616 have been merged
    # CSP_CONFIG_VER2_5,  # If none of the above have been merged
    CSP_DELAYMODEL_VER3_0,
    CSP_SCAN_VER2_3,
    CSP_INITSYSPARAM_VER1_0,
]

supported_interfaces = {
    "config": CSP_CONFIG_VERSIONS,
    "delaymodel": CSP_DELAYMODEL_VERSIONS,
    "scan": CSP_SCAN_VERSIONS,
    "initsysparam": CSP_INITSYSPARAM_VERSIONS,
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
    # if input["interface"] not in SUPPORTED_INTERFACES:
    if not any(
        input["interface"] in val for val in supported_interfaces.values()
    ):
        print(SUPPORTED_INTERFACES)
        return [False, "The command interface is not supported"]

    # Return pass
    return [True, ""]
