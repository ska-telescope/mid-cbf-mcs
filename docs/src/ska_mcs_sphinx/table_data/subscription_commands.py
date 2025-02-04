from inspect import cleandoc
from ska_mid_cbf_mcs.commons.validate_interface import supported_interfaces

subscription_commands_data = {
    "headers": [
        "Subscription",
        "Parameters",
        "Action",
        "Supported Interface(s)"
    ],
    "data": [
        { 
            "Subscription": "Delay Model",
            "Parameters": "JSON str*",
            "Action": cleandoc(
                """
                Pass DISH ID as VCC ID integer to FSPs and VCCs
                Update VCC Delay Model
                Update FSP Delay Model
                """),   
            "Supported Interface(s)": supported_interfaces["delaymodel"],
        },
    ]
}
