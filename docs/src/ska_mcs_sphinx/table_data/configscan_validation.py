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
            "Scan Configuration Parameter": "test",
            "AA4 Ranges (see TM)": cleandoc(
                """
                some ``formated`` text here.
                
                some *italic* text here.
                
                some **bold** text here.
                """),
            "Supported": cleandoc(
                """
                this is a literal block::

                    This is the first line of a ``not processed`` line
                    
                    This is the **second** line which is not *processed*
                    
                This is normal text again
                """),
            "Comment": cleandoc(
                """
                a list of items:
                
                #. check 1
                #. check 2
                
                   * Sub-point 1
                   * Sub-point 2
                
                #. check 3
                
                """),
        },
        {
            "Scan Configuration Parameter": "other",
            "AA4 Ranges (see TM)": "0 - 24",
            "Supported": cleandoc(
                """
                calls code:
                
                .. code-block:: bash
                
                   echo $\{host\} && curl 8.8.8.8
                   cat /src/test.txt | grep "hello"
                
                """),
            "Comment": cleandoc(
                """
                .. warning::

                   This value is currently unsupported.

                using this will result in unexpected behaviour.

                """),
        }
    ]
}
