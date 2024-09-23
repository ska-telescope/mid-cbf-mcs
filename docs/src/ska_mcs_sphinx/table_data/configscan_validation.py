from inspect import cleandoc

configurescan_validation_rules_data = {
    "headers": [
        "Scan Configuration Parameter",
        "AA4 Ranges (see TM)",
        "Supported",
        "Comment"
    ], 
    "data": [
        {
            "Scan Configuration Parameter": "subarray_id",
            "AA4 Ranges (see TM)": "1 - 16",
            "Supported": "1",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "fsp_ids",
            "AA4 Ranges (see TM)": "Array of 1 to 26 fsp_id",
            "Supported": "Array of 1 to 4 fsp_id",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "fsp_id",
            "AA4 Ranges (see TM)": "1 - 27",
            "Supported": cleandoc(
                """
                Complex:
                
                * if CORR: 1 - 4
                
                """
                ),
            "Comment": "PST: 5 - 8 when implemented",
        },
        {
            "Scan Configuration Parameter": "band_5_tuning",
            "AA4 Ranges (see TM)": "See TM",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
        {
            "Scan Configuration Parameter": "frequency_band",
            "AA4 Ranges (see TM)": "1, 2, 5a, 5b",
            "Supported": "1, 2",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "frequency_band_offset_stream1",
            "AA4 Ranges (see TM)": "See TM",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
        {
            "Scan Configuration Parameter": "frequency_band_offset_stream2",
            "AA4 Ranges (see TM)":  "See TM",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
        {
            "Scan Configuration Parameter": "rfi_flagging_mask",
            "AA4 Ranges (see TM)":  "See TM",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
        {
            "Scan Configuration Parameter": "receptors",
            "AA4 Ranges (see TM)": "all SKA and MKT",
            "Supported": "all",
            "Comment": "No additional check needed",
        },
        {
            "Scan Configuration Parameter": "start_freq",
            "AA4 Ranges (see TM)":  "See TM",
            "Supported":  cleandoc(
                """
                Complex check

                * Entire processing region must fall inside specified band
                
                * Required bandwidth [start_freq - (1/2 * start_freq) +
                (channel_width * channel_count)] must not require more FSP's
                than provided in fsp_ids

                """),
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "channel_width",
            "AA4 Ranges (see TM)": "See TM for enumT",
            "Supported": "13440",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "channel_count",
            "AA4 Ranges (see TM)": "See TM",
            "Supported": cleandoc(
                """
                * Integer from 1 to 58982 inclusive
                
                * Must be a multiple of 20
                """
                ),
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "sdp_start_channel_id",
            "AA4 Ranges (see TM)": "See TM",
            "Supported": "Same as TM",
            "Comment": "No additional check needed",
        },
        {
            "Scan Configuration Parameter": "integration_factor",
            "AA4 Ranges (see TM)": "1 - 10",
            "Supported": "1 - 10",
            "Comment": "No additional check needed",
        },
        {
            "Scan Configuration Parameter": "output_port",
            "AA4 Ranges (see TM)": "1 - 10",
            "Supported": "1 - 10",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "output_link_map",
            "AA4 Ranges (see TM)": "1 - 10",
            "Supported": "[[sdp_start_channel_id, 1]]",
            "Comment": "",
        },
        {
            "Scan Configuration Parameter": "vlbi",
            "AA4 Ranges (see TM)": "",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
        {
            "Scan Configuration Parameter": "search_window",
            "AA4 Ranges (see TM)": "",
            "Supported": "None",
            "Comment": cleandoc(
                """
                .. warning::

                    This value is currently unsupported.

                    Using this value will result in a rejected scan configuration

                """),
        },
    ]
}
