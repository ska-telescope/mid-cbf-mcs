from inspect import cleandoc

configurescan_validation_rules = [
    {
        "Scan Configuration Parameter": "",
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
            
            * check 1
            * check 2
            
              * Sub-point 1
              * Sub-point 2
            
            * check 3
            
            """),
    }
]