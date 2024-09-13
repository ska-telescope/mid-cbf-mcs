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
            .. warning::
                This is a warning block
            
                This value is not supported yet!
            """),
        "Comment": cleandoc(
            """
            complex check:
            
            #. check 1
            #. check 2
            
               * Sub-point 1

               * Sub-point 2
            
            #. check 3
            
            """),
    }
]