import os.path
import json
from traceback import format_exception, format_exception_only
import yaml
from collections import OrderedDict
import pathlib

from docutils import nodes, utils
from docutils.parsers.rst import Directive, DirectiveError
from docutils.parsers.rst import directives
from docutils.utils import SystemMessagePropagation

from ska_mid_cbf_mcs.commons.validate_interface import supported_interfaces

import importlib

HEADER_LIST = ['Command', 'Parameters', 'Return type', 'Action', 'Supported Interface']

CONTROLLER_OFF_COMMAND = ['Off', 'None', '(ResultCode, str)', 'Set power state to OFF for controller and subordinate devices (subarrays, VCCs, FSPs)\nTurn off power to all hardware\nSee also :ref:\'Off Sequence\'']

COMMANDS_LIST = ['Off', 'On', 'Config']

cbf_controller_table = {
    "header": ['Command', 'Parameters', 'Return type', 'Action', 'Supported interface'],
    "row1": ['Off', 'None', '(ResultCode, str)', 'Set power state to OFF for controller and subordinate devices (subarrays, VCCs, FSPs)\nTurn off power to all hardware\nSee also :ref:\'Off Sequence\'', None],
    "row2": ['InitSysParam', 'JSON str*', '(ResultCode, str)', 'Initialize Dish ID to VCC ID mapping and k values\n:ref:\'See also InitSysParam Sequence\'', f'{supported_interfaces["config"]}'],
    "row3": ['Standby', 'None', '(ResultCode, str)', 'None', None],
    "row4": ['On', 'None', '(ResultCode, str)', 'Turn on the controller and subordinate devices', None],
}

num_cols = cbf_controller_table['header'].size()


# Variables: num_rows, command_list, param_list, return_list, action_list, supported_versions_list
# TODO: For supported versions we can read param list and if json is found we can
#       look for command with matching prefix as supported versions

class SkaTables(Directive):
    has_content = True


    def run(self):

        table = nodes.table()

        tgroup = nodes.tgroup(cols = 5)
        colspec_1 = nodes.colspec(colwidth=10)
        colspec_2 = nodes.colspec(colwidth=10)
        colspec_3 = nodes.colspec(colwidth=10)
        colspec_4 = nodes.colspec(colwidth=10)
        colspec_5 = nodes.colspec(colwidth=10)
        header = nodes.thead()
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
        row2 = nodes.row()
        row3 = nodes.row()
        row4 = nodes.row()
 
        for i in range(num_cols):
            r1_entry = nodes.entry('', nodes.paragraph(text=cbf_controller_table['row1'][i]))
            r2_entry = nodes.entry('', nodes.paragraph(text=cbf_controller_table['row2'][i]))
            r3_entry = nodes.entry('', nodes.paragraph(text=cbf_controller_table['row3'][i]))
            r4_entry = nodes.entry('', nodes.paragraph(text=cbf_controller_table['row4'][i]))

            row1 += r1_entry
            row2 += r2_entry
            row3 += r3_entry
            row4 += r4_entry

        table_body += row1
        table_body += row2
        table_body += row3
        table_body += row4


        # row1 = nodes.row()
        # r1_c1_entry = nodes.entry('', nodes.paragraph(text='no'))
        # r1_c2_entry = nodes.entry('', nodes.paragraph(text='no'))
        # r1_c3_entry = nodes.entry('', nodes.paragraph(text='no'))
        # r1_c4_entry = nodes.entry('', nodes.paragraph(text='no'))
        # r1_c5_entry = nodes.entry('', nodes.paragraph(text='no'))

        # r1_c5_entry = nodes.entry('', nodes.paragraph(text="""Set power state to OFF for controller and \
        #                             subordinate devices (subarrays, VCCs, FSPs)\
        #                             Turn off power to all hardware\
        #                             See also :ref:'Off Sequence'"""))          # Test if this works in rst
        # row1  +=  (r1_c1_entry)
        # row1  +=  (r1_c2_entry)
        # row1  +=  (r1_c3_entry)
        # row1  +=  (r1_c4_entry)
        # row1  +=  (r1_c5_entry)

        # table_body  +=  (row1)

        table  +=  (tgroup)
        tgroup  +=  (colspec_1)
        tgroup  +=  (colspec_2)
        tgroup  +=  (colspec_3)
        tgroup  +=  (colspec_4)
        tgroup  +=  (colspec_5)
        tgroup  +=  (header)
        tgroup  +=  (table_body)


        return [table]


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

def main():
    print(cbf_controller_table['row2'][4])
    print(cbf_controller_table['row1'])

if __name__ == "__main__":
    main()