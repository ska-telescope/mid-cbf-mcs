import os.path
import json
from traceback import format_exception, format_exception_only
import yaml
from collections import OrderedDict
import pathlib

from inspect import cleandoc
from docutils import nodes, utils
from docutils.parsers.rst import Directive, DirectiveError
from docutils.parsers.rst import directives
from docutils.utils import SystemMessagePropagation

from sphinx.util.nodes import nested_parse_with_titles

import importlib

HEADER_LIST = ['Command', 'Parameters', 'Return type', 'Action', 'Supported Interface']

test_reference_string =  cleandoc(
    """
    | Text
    | Some values
    | See also :ref:`Abort Sequence`
    """
)

# Variables: num_rows, command_list, param_list, return_list, action_list, supported_versions_list
# TODO: For supported versions we can read param list and if json is found we can
#       look for command with matching prefix as supported versions

class SkaTables(Directive):
    # required_arguments = 5
    optional_arguments = 5
    has_content = True


    def run(self):

        

        table = nodes.table()

        tgroup = nodes.tgroup(cols = 5)
        colspec_1 = nodes.colspec(colwidth=10)           # Spec for each column needed
        colspec_2 = nodes.colspec(colwidth=10)
        colspec_3 = nodes.colspec(colwidth=10)
        colspec_4 = nodes.colspec(colwidth=10)
        colspec_5 = nodes.colspec(colwidth=10)
        header = nodes.thead()              # Need variable or can just call?
        header_row = nodes.row()
        header_1 = nodes.entry('', nodes.paragraph(text=HEADER_LIST[0]))
        header_2 = nodes.entry('', nodes.paragraph(text=HEADER_LIST[1]))
        header_3 = nodes.entry('', nodes.paragraph(text=HEADER_LIST[2]))
        header_4 = nodes.entry('', nodes.paragraph(text=HEADER_LIST[3]))
        header_5 = nodes.entry('', nodes.paragraph(text=HEADER_LIST[4]))
        header_row  +=  (header_1)
        header_row  +=  (header_2)
        header_row  +=  (header_3)
        header_row  +=  (header_4)
        header_row  +=  (header_5)

        header  +=  (header_row)       # Assume this is right


        table_body = nodes.tbody()

        row1 = nodes.row()
        r1_c1_entry = nodes.entry('', nodes.paragraph(text='no'))
        r1_c2_entry = nodes.entry('', nodes.paragraph(text='no'))
        r1_c3_entry = nodes.entry('', nodes.paragraph(text='no'))
        r1_c4_entry = nodes.entry('', nodes.paragraph(text='no'))
        r1_c5_entry = nodes.entry('', nodes.paragraph(text='no'))
        
        r1_c5_entry = nodes.entry('', self._parse_text(test_reference_string))          # Test if this works in rst
        
        
        row1  +=  (r1_c1_entry)
        row1  +=  (r1_c2_entry)
        row1  +=  (r1_c3_entry)
        row1  +=  (r1_c4_entry)
        row1  +=  (r1_c5_entry)

        table_body  +=  (row1)

        table  +=  (tgroup)
        tgroup  +=  (colspec_1)
        tgroup  +=  (colspec_2)
        tgroup  +=  (colspec_3)
        tgroup  +=  (colspec_4)
        tgroup  +=  (colspec_5)
        tgroup  +=  (header)
        tgroup  +=  (table_body)
        
        return [table]


    def _parse_text(self, text: str):
        p_node = nodes.paragraph(text=text)
        # Create a node.
        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, p_node, node)
        return node.children


class HelloDirective(Directive):
    """A directive to say hello and create a table!"""

    def run(self) -> list[nodes.Node]:
        # Create the main table node
        table = nodes.table()
        
        # Create the tgroup (table group) node
        tgroup = nodes.tgroup(cols=2)
        table += tgroup
        
        # Add column specifications
        tgroup += nodes.colspec(colwidth=8)
        tgroup += nodes.colspec(colwidth=4)
        
        # Add table header
        thead = nodes.thead()
        tgroup += thead
        header_row = nodes.row()
        thead += header_row
        header_row += nodes.entry('', nodes.paragraph(text='Item'))
        header_row += nodes.entry('', nodes.paragraph(text='Code'))
        
        # Add table body
        tbody = nodes.tbody()
        tgroup += tbody
        
        # Add rows to the body
        row_1 = nodes.row()
        row_1 += nodes.entry('', nodes.paragraph(text='bread'))
        row_1 += nodes.entry('', nodes.paragraph(text='E2'))
        tbody += row_1
        
        row_2 = nodes.row()
        row_2 += nodes.entry('', nodes.paragraph(text='butter'))
        row_2 += nodes.entry('', nodes.paragraph(text='E30'))
        tbody += row_2
        
        return [table]


