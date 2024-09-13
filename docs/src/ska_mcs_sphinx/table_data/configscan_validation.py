from inspect import cleandoc

configurescan_validation_rules = {
    "headers": [
        "Scan Configuration Parameter",
        "AA4 Ranges (see TM)",
        "Supported",
        "Comment"
    ], 
    "data": [
        {
            "Scan Configuration Parameter": "other",
            "AA4 Ranges (see TM)": "some value",
            "Supported": "a subset of the value",
            "Comment": "no comment",
        },
        {
            "Scan Configuration Parameter": "other",
            "AA4 Ranges (see TM)": "some value",
            "Supported": "a subset of the value",
            "Comment": "no comment",
        }
    ]
}
