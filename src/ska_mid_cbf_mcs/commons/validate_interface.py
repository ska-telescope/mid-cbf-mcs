import json

from ska_telmodel.csp.version import (
    CSP_CONFIG_PREFIX,
    CSP_CONFIGSCAN_PREFIX,
    CSP_MID_DELAYMODEL_PREFIX,
    CSP_SCAN_PREFIX,
)

CBF_INITSYSPARAM_PREFIX = "https://schema.skao.int/ska-mid-cbf-initsysparam/"

CSP_CONFIGSCAN_VER3_0 = CSP_CONFIGSCAN_PREFIX + "3.0"
CSP_CONFIGSCAN_VER4_1 = CSP_CONFIGSCAN_PREFIX + "4.1"
CSP_CONFIGSCAN_VER2_5 = CSP_CONFIG_PREFIX + "2.5"

CSP_MID_DELAYMODEL_VER3_0 = CSP_MID_DELAYMODEL_PREFIX + "3.0"

CSP_SCAN_VER2_3 = CSP_SCAN_PREFIX + "2.3"

CBF_INITSYSPARAM_VER1_0 = CBF_INITSYSPARAM_PREFIX + "1.0"


CSP_CONFIGSCAN_VERSIONS = [
    CSP_CONFIGSCAN_VER3_0,
    # CSP_CONFIGSCAN_VER4_1,
    # CSP_CONFIGSCAN_VER2_5,
]
CSP_MID_DELAYMODEL_VERSIONS = [CSP_MID_DELAYMODEL_VER3_0]
CSP_SCAN_VERSIONS = [CSP_SCAN_VER2_3]
CBF_INITSYSPARAM_VERSIONS = [CBF_INITSYSPARAM_VER1_0]


supported_interfaces = {
    "configurescan": CSP_CONFIGSCAN_VERSIONS,
    "delaymodel": CSP_MID_DELAYMODEL_VERSIONS,
    "scan": CSP_SCAN_VERSIONS,
    "initsysparam": CBF_INITSYSPARAM_VERSIONS,
}

command_mapping = {
    "configure": CSP_CONFIG_PREFIX, 
    "configurescan": CSP_CONFIGSCAN_PREFIX,
    "delaymodel": CSP_MID_DELAYMODEL_PREFIX,
    "scan": CSP_SCAN_PREFIX,
    "initsysparam": CBF_INITSYSPARAM_PREFIX,
}

__all__ = ["ValidateInterface", "main"]


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

    # Check intended command
    if command_mapping[command] not in input["interface"]:
        return [
            False,
            "The input interface does not match the intended command",
        ]    
    
    # Check supported interface
    if not any(
        input["interface"] in val for val in supported_interfaces.values()
    ):
        return [False, "The command interface is not supported"]
    
    # Return pass
    return [True, ""]


# Unit tests    

def validation_test():

    input_txt = """
                    hello
                    """

    input_no_key = """
                    {
                    "scan_id": 7, 
                    "transaction_id": "txn-....-00001"
                    }
                    """

    input_not_string = """
                    {
                    "interface": 5, 
                    "scan_id": 1,
                    "transaction_id": "txn-....-00001"
                    }
                    """


    input_configscan_supported = """
                    {
                    "interface": "https://schema.skao.int/ska-csp-configurescan/3.0", 
                    "scan_id": 1,
                    "transaction_id": "txn-....-00001"
                    }
                    """

    input_configscan_unsupported = """
                    {
                    "interface": "https://schema.skao.int/ska-csp-configurescan/30.0", 
                    "scan_id": 1,
                    "transaction_id": "txn-....-00001"
                    }
                    """

    input_scan_supported = """
                    {
                    "interface": "https://schema.skao.int/ska-csp-scan/2.3", 
                    "scan_id": 1,
                    "transaction_id": "txn-....-00001"
                    }
                    """

    input_scan_unsupported = """
                    {
                    "interface": "https://schema.skao.int/ska-csp-scan/23.0", 
                    "scan_id": 1,
                    "transaction_id": "txn-....-00001"
                    }
                    """

    input_initsysparam_supported = """
                    {
                    "interface": "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0", 
                    "scan_id": 1,
                    "transaction_id": "txn-....-00001"
                    }
                    """

    input_initsysparam_unsupported = """
                    {
                    "interface": "https://schema.skao.int/ska-mid-cbf-initsysparam/10.0", 
                    "scan_id": 1,
                    "transaction_id": "txn-....-00001"
                    }
                    """

    input_delaymodel_supported = """
                    {
                    "interface": "https://schema.skao.int/ska-mid-csp-delaymodel/3.0", 
                    "scan_id": 1,
                    "transaction_id": "txn-....-00001"
                    }
                    """

    input_delaymodel_unsupported = """
                    {
                    "interface": "https://schema.skao.int/ska-mid-csp-delaymodel/30.0", 
                    "scan_id": 1,
                    "transaction_id": "txn-....-00001"
                    }
                    """

    input_lowconfigscan = """
                    {
                    "interface": "https://schema.skao.int/ska-low-cbf-configurescan/1.0", 
                    "scan_id": 1,
                    "transaction_id": "txn-....-00001"
                    }
                    """

    print(validate_interface(input_txt, "scan"))
    print(validate_interface(input_no_key, "scan"))
    print(validate_interface(input_not_string, "scan"))
    print(validate_interface(input_configscan_supported, "scan"))
    print("\n")
    print(validate_interface(input_configscan_supported, "configurescan"))
    print(validate_interface(input_configscan_unsupported, "configurescan"))
    print("\n")
    print(validate_interface(input_scan_supported, "scan"))
    print(validate_interface(input_scan_unsupported, "scan"))
    print("\n")
    print(validate_interface(input_initsysparam_supported, "initsysparam"))
    print(validate_interface(input_initsysparam_unsupported, "initsysparam"))
    print("\n")
    print(validate_interface(input_delaymodel_supported, "delaymodel"))
    print(validate_interface(input_delaymodel_unsupported, "delaymodel"))
    print("\n")
    print(validate_interface(input_lowconfigscan, "configure"))



def main():
    validation_test()
    


if __name__ == "__main__":
    main()
