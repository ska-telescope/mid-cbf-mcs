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

test_reference_string = cleandoc(
    """
    Text
    Some values
    That we want in this break order
    See also :ref:`Abort Sequence`
    """
)

test_non_block = cleandoc(
    """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Maecena
    amet, fringilla est. :ref:`Abort Sequence` Cras nulla tellus.
    """
)

test_interfaces = [
    "https://schema.skao.int/ska-csp-configurescan/4.3"
    "https://schema.skao.int/ska-csp-configurescan/4.2"
    "https://schema.skao.int/ska-csp-configurescan/4.1"
]


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
        
        
        r1_c4_entry = nodes.entry('')
        r1_c4_entry.append(self._parse_line_block(test_reference_string))
        
        r1_c5_entry = nodes.entry('')          # Test if this works in rst
        r1_c5_entry.append(self._create_unordered_list(test_interfaces))
        row1  +=  (r1_c1_entry)
        row1  +=  (r1_c2_entry)
        row1  +=  (r1_c3_entry)
        row1  +=  (r1_c4_entry)
        row1  +=  (r1_c5_entry)
        
        row2 = nodes.row
        row2 += nodes.entry('', nodes.paragraph(text= "1"))
        row2 += nodes.entry('', nodes.paragraph(text= "2"))
        row2 += nodes.entry('', nodes.paragraph(text= "3"))
        
        entry1 = nodes.entry('')
        entry1.append(self._parse_line_block(test_reference_string))
        row2 += entry1
        
        entry2 = nodes.entry('')
        entry2.append(self._create_line_block_from_list(test_interfaces))
        row2 += entry2

        table_body  +=  (row1)
        table_body += (row2)

        table  +=  (tgroup)
        tgroup  +=  (colspec_1)
        tgroup  +=  (colspec_2)
        tgroup  +=  (colspec_3)
        tgroup  +=  (colspec_4)
        tgroup  +=  (colspec_5)
        tgroup  +=  (header)
        tgroup  +=  (table_body)
        
        return[table]


    def _parse_text(self, text_to_parse: str):
        p_node = nodes.paragraph(text=text_to_parse,)
        # Create a node.
        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, p_node, node)
        return node.children
    
    def _parse_paragraph(self, text_to_parse: str):
        paragraph = nodes.paragraph()
        paragraph.children = self._parse_text(text_to_parse)
        return paragraph
    
    def _parse_line_block(self, text_to_parse: str):
        lines = text_to_parse.split('\n')
        line_block = nodes.line_block()
        for line_entry in lines:
            line = nodes.line()
            line.children = self._parse_text(line_entry)
            line_block.append(line)
        return line_block

    def _create_unordered_list(self, list_items: list[str]):
        unordered_list = nodes.bullet_list()
        for item in list_items:
            list_item = nodes.list_item()
            list_item += nodes.paragraph(text=item)
            unordered_list += list_item
        return unordered_list
    
    def _create_line_block_from_list(self, list_items: list[str]):
        line_block = nodes.line_block()
        for item in list_items:
            line = nodes.line(text=item)
            line_block += line
        return line_block
            
        


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


