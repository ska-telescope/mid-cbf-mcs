from inspect import cleandoc
from ska_mid_cbf_mcs.commons.validate_interface import supported_interfaces

subarray_commands_data = {
    "headers": [
        "Command",
        "Parameters",
        "Return Type",
        "Action",
        "Supported Interface(s)"
    ],
    "data": [
        { 
            "Command": "Abort",
            "Parameters": "None",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                Change observing state to ABORTED
                Send Abort to VCC
                Send Abort to FSP <function mode> Subarrays
                No action on hardware
                See also :ref:`Abort Sequence`
                """),
        },
        { 
            "Command": "AddReceptors",
            "Parameters": "List[str]",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                Assign receptors to this subarray
                Turn subarray to ObsState = IDLE if no
                receptor was previously assigned
                """),
        },
        { 
            "Command": "ConfigureScan",
            "Parameters": "JSON str*",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                Change observing state to READY
                Configure attributes from input JSON
                Subscribe events
                Configure VCC, VCC subarray, FSP, FSP Subarray
                Publish output links.
                See also :ref:`Configure Scan Sequence`
                """),   
            "Supported Interface(s)": supported_interfaces['configurescan'],
        },
        { 
            "Command": "EndScan",
            "Parameters": "None",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                End the scan
                """),
        },
        { 
            "Command": "ObsReset",
            "Parameters": "None",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                Reset subarray scan configuration
                Keep assigned receptors
                Reset observing state to IDLE
                If in FAULT, send Abort/ObsReset to VCC
                If in FAULT, send Abort/ObsReset to
                FSP <function mode> subarrays
                No action on hardware
                See also :ref:`ObsReset Sequence`
                """    
            ),
        },
        { 
            "Command": "Off",
            "Parameters": "None",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                Set subarray power mode to off.
                Commands FSP<function mode> Subarrays
                to turn off
                No action on hardware power
                """),
        },
        { 
            "Command": "On",
            "Parameters": "None",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                Set subarry power mode to on.
                Command FSP<function mode> Subarrays
                to turn on
                """),
        },
        { 
            "Command": "RemoveAllReceptors",
            "Parameters": "None",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                Remove all receptors
                Turn Subarray off if no receptors are
                assigned
                """),
        },
        { 
            "Command": "RemoveReceptors",
            "Parameters": "List[str]",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                Remove receptors in input list
                Change observing state to EMPTY if no
                receptors assigned
                """),
        },
        { 
            "Command": "Restart",
            "Parameters": "None",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                Reset subarray scan configuration
                Remove assigned receptors
                Restart observing state model to EMPTY
                If in FAULT, send Abort/ObsReset to VCC
                If in FAULT, send Abort/ObsReset to
                FSP <function mode> subarrays
                No action on hardware
                See also :ref:`Restart Sequence`
                """),
        },
        { 
            "Command": "Scan",
            "Parameters": "JSON str*",
            "Return Type": "(ResultCode, str)",
            "Action": cleandoc(
                """
                Start scanning
                """),   
            "Supported Interface(s)": supported_interfaces['scan'],
        },
    ]
}
