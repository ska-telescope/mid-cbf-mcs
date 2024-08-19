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

from ska_mid_cbf_mcs.commons.validate_interface import supported_interfaces

from sphinx.util.nodes import nested_parse_with_titles

import importlib

HEADER_LIST = ['Command', 'Parameters', 'Return type', 'Action', 'Supported Interface']

cbf_controller_table = {
    "header": ['Command', 'Parameters', 'Return type', 'Action', 'Supported interface'],
    "row1": ['Off', 'None', '(ResultCode, str)', 'Set power state to OFF for controller and subordinate devices (subarrays, VCCs, FSPs)\nTurn off power to all hardware\nSee also :ref:\'Off Sequence\'', ''],
    "row2": ['InitSysParam', 'JSON str*', '(ResultCode, str)', 'Initialize Dish ID to VCC ID mapping and k values\n:ref:\'See also InitSysParam Sequence\'', f'{supported_interfaces["config"]}'],
    "row3": ['Standby', 'None', '(ResultCode, str)', 'None', ''],
    "row4": ['On', 'None', '(ResultCode, str)', 'Turn on the controller and subordinate devices', ''],
}

controller_num_cols = len(cbf_controller_table['header'])


cbf_subarray_table = {
    "header": ['Command', 'Parameters', 'Return type', 'Action', 'Supported interface'],
    "row1": ['Abort', 'None', '(ResultCode, str)', 'Change observing state to ABORTED\nSend Abort to VCC\n Send Abort to FSP <function mode> Subarrays\nNo action on hardware\nSee also :ref:\'Abort Sequence\'', ''],
    "row2": ['AddReceptors', 'List[str]', '(ResultCode, str)', 'Assign receptors to this subarray\nTurn subarray to ObsState = IDLE if no\nreceptor was previously assigned', ''],
    "row3": ['ConfigureScan', 'JSON str*', '(ResultCode, str)', 'Change observing state to READY\nConfigure attributes from input JSON\nSubscribe events\nConfigure VCC,\
             VCC subarray, FSP, FSP Subarray\nPublish output links.\nSee also :ref:\'Configure Scan Sequence\'', f'{supported_interfaces["config"]}'],
    "row4": ['EndScan', 'None', '(ResultCode, str)', 'End the scan', ''],
    "row5": ['ObsReset', 'None', '(ResultCode, str)', 'Reset subarray scan configuration\nKeep assigned receptors\nReset observing state to IDLE\nIf in FAULT, send Abort/ObsReset to VCC\
             If in FAULT, send Abort/ObsReset to\nFSP <function mode> subarrays\nNo action on hardware\nSee also :ref:\'ObsReset Sequence\'', ''],
    "row6": ['Off', 'None', '(ResultCode, str)', 'Set subarray power mode to off.\nCommands FSP<function mode> Subarrays\nto turn off\nNo action on hardware power', ''],
    "row7": ['On', 'None', '(ResultCode, str)', 'Set subarry power mode to on.\nCommand FSP<function mode> Subarrays\nto turn on', ''],
    "row8": ['RemoveAllReceptrs', 'None', '(ResultCode, str)', 'Remove all receptors\nTurn Subarray off if no receptors are\nassigned', ''],
    "row9": ['RemoveReceptors', 'List[str]', '(ResultCode, str)', 'Remove receptors in input list\nChange observing state to EMPTY if no\nreceptors assigned', ''],
    "row10": ['Restart', 'None', '(ResultCode, str)', 'Reset subarray scan configuration\nRemove assigned receptors\nRestart observing state model to EMPTY\
              If in FAULT, send Abort/ObsReset to VCC\nIf in FAULT, send Abort/ObsReset to\nFSP <function mode> subarrays\nNo action on hardware\nSee also Restart Sequence', ''],
    "row11": ['Scan', 'JSON str*', '(ResultCode, str)', 'Start scanning', f'{supported_interfaces["scan"]}'],
}

subarray_num_cols = len(cbf_subarray_table['header'])

controller_commands = [
    { 
        "Command": "Off",
        "Parameters": "None",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Set power state to OFF for controller and
            subordinate devices (subarrays, VCCs, FSPs)
            Turn off power to all hardware
            See also :ref:'Off Sequence'
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "InitSysParam",
        "Parameters": "JSON str*",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Initialize Dish ID to VCC ID mapping and k values
            See also :ref:`Configure Scan Sequence`
            """),   
        "Supported Interface(s)": str(supported_interfaces["initsysparam"]),
    },
    { 
        "Command": "Standby",
        "Parameters": "None",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            None
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "On",
        "Parameters": "None",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Turn on the controller and subordinate devices
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "ConfigureScan",
        "Parameters": "JSON str*",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            TEST
            Change observing state to READY
            Configure attributes from input JSON
            Subscribe events
            Configure VCC, VCC subarray, FSP, FSP Subarray
            Publish output links.
            See also :ref:`Configure Scan Sequence`
            """    
        ),
        "Supported Interface(s)": [
            "https://schema.skao.int/ska-csp-configurescan/4.3",
            "https://schema.skao.int/ska-csp-configurescan/4.2",
            "https://schema.skao.int/ska-csp-configurescan/4.1"
        ],
    }
]


subarray_commands = [
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
            See also :ref:`Configure Scan Sequence`
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "InitSysParam",
        "Parameters": "JSON str*",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Initialize Dish ID to VCC ID mapping and k values
            See also :ref:'InitSysParam Sequence'
            """),   
        "Supported Interface(s)": str(supported_interfaces["initsysparam"]),
    },
    { 
        "Command": "Standby",
        "Parameters": "None",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            None
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "On",
        "Parameters": "None",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Turn on the controller and subordinate devices
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "ConfigureScan",
        "Parameters": "JSON str*",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            TEST
            Change observing state to READY
            Configure attributes from input JSON
            Subscribe events
            Configure VCC, VCC subarray, FSP, FSP Subarray
            Publish output links.
            See also :ref:`Configure Scan Sequence`
            """    
        ),
        "Supported Interface(s)": [
            "https://schema.skao.int/ska-csp-configurescan/4.3",
            "https://schema.skao.int/ska-csp-configurescan/4.2",
            "https://schema.skao.int/ska-csp-configurescan/4.1"
        ],
    }
]


# Variables: num_rows, command_list, param_list, return_list, action_list, supported_versions_list
# TODO: For supported versions we can read param list and if json is found we can
#       look for command with matching prefix as supported versions

class CbfControllerTable(Directive):
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

        header  +=  (header_row)

        table_body = nodes.tbody()

        for index, command in enumerate(controller_commands):
            row_class = 'row-even' if index % 2 == 0 else 'row-odd'
            row = nodes.row("", classes=[row_class])
            row.append(nodes.entry('', nodes.paragraph(text=command['Command'])))
            row.append(nodes.entry('', nodes.paragraph(text=command['Parameters'])))
            row.append(nodes.entry('', nodes.paragraph(text=command['Return Type'])))
            action_entry = nodes.entry('')
            action_entry.append(self._parse_line_block(command['Action']))
            row.append(action_entry)
            supported_entry = nodes.entry('')
            supported_entry.append(self._create_line_block_from_list(command['Supported Interface(s)']))
            row.append(supported_entry)
            table_body.append(row)

        table  +=  (tgroup)
        tgroup  +=  (colspec_1)
        tgroup  +=  (colspec_2)
        tgroup  +=  (colspec_3)
        tgroup  +=  (colspec_4)
        tgroup  +=  (colspec_5)
        tgroup  +=  (header)
        tgroup  +=  (table_body)


        return [table]
    
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
            parsed = self._parse_text(line_entry)
            line.children = parsed[0].children
            line_block.append(line)
        return line_block

    def _create_unordered_list(self, list_items: list[str]):
        unordered_list = nodes.bullet_list()
        for item in list_items:
            list_item = nodes.list_item()
            list_item.append(nodes.paragraph(text=item))
            unordered_list.append(list_item)
        return unordered_list
    
    def _create_line_block_from_list(self, list_items: list[str]):
        line_block = nodes.line_block()
        for item in list_items:
            line = nodes.line(text=item)
            line_block.append(line)
        return line_block




class CbfSubarrayTable(Directive):
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

        header  +=  (header_row)

        table_body = nodes.tbody()

        row1 = nodes.row()
        row2 = nodes.row()
        row3 = nodes.row()
        row4 = nodes.row()
        row5 = nodes.row()
        row6 = nodes.row()
        row7 = nodes.row()
        row8 = nodes.row()
        row9 = nodes.row()
        row10 = nodes.row()
        row11 = nodes.row()
 
        for i in range(subarray_num_cols):
            r1_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row1'][i]))
            r2_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row2'][i]))
            r3_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row3'][i]))
            r4_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row4'][i]))
            r5_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row5'][i]))
            r6_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row6'][i]))
            r7_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row7'][i]))
            r8_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row8'][i]))
            r9_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row9'][i]))
            r10_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row10'][i]))
            r11_entry = nodes.entry('', nodes.paragraph(text=cbf_subarray_table['row11'][i]))

            row1 += r1_entry
            row2 += r2_entry
            row3 += r3_entry
            row4 += r4_entry
            row5 += r5_entry
            row6 += r6_entry
            row7 += r7_entry
            row8 += r8_entry
            row9 += r9_entry
            row10 += r10_entry
            row11 += r11_entry

        table_body += row1
        table_body += row2
        table_body += row3
        table_body += row4
        table_body += row5
        table_body += row6
        table_body += row7
        table_body += row8
        table_body += row9
        table_body += row10
        table_body += row11

        table  +=  (tgroup)
        tgroup  +=  (colspec_1)
        tgroup  +=  (colspec_2)
        tgroup  +=  (colspec_3)
        tgroup  +=  (colspec_4)
        tgroup  +=  (colspec_5)
        tgroup  +=  (header)
        tgroup  +=  (table_body)

        return [table]


def main():
    print(cbf_subarray_table['row2'][4])
    print(cbf_subarray_table['row1'])

if __name__ == "__main__":
    main()


