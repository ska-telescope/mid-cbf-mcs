from inspect import cleandoc
from ska_mid_cbf_mcs.commons.validate_interface import supported_interfaces

controller_commands = [
    { 
        "Command": "Off",
        "Parameters": "None",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Set power state to OFF for controller and
            subordinate devices (subarrays, VCCs, FSPs)
            Turn off power to all hardware
            See also :ref:`Off Sequence`
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "InitSysParam",
        "Parameters": "JSON str*",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Initialize Dish ID to VCC ID mapping and k values
            See also :ref:`InitSysParam Sequence`
            """),   
        "Supported Interface(s)": supported_interfaces['initsysparam'],
    },
    { 
        "Command": "Standby",
        "Parameters": "None",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            None
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "On",
        "Parameters": "None",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Turn on the controller and subordinate devices
            """),   
        "Supported Interface(s)": '',
    },
]
