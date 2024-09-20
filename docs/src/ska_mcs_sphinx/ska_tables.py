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

HEADER_LIST = ['Command', 'Parameters', 'Long Running Command', 'Return type', 'Action', 'Supported Interface(s)']

controller_commands = [
    { 
        "Command": "Off",
        "Parameters": "None",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Set power state to OFF for controller and
            subordinate devices (subarrays, VCCs, FSPs)
            Turn off power to all hardware
            See also :ref:`Off Sequence`
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "InitSysParam",
        "Parameters": "JSON str*",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Initialize Dish ID to VCC ID mapping and k values
            See also :ref:`InitSysParam Sequence`
            """),   
        "Supported Interface(s)": supported_interfaces['initsysparam'],
    },
    { 
        "Command": "On",
        "Parameters": "None",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Turn on the controller and subordinate devices
            """),   
        "Supported Interface(s)": '',
    },
]

subarray_commands = [
    { 
        "Command": "Abort",
        "Parameters": "None",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Change observing state to ABORTED
            Send Abort to VCC
            Send Abort to FSP <function mode> Subarrays
            No action on hardware
            See also :ref:`Abort Sequence`
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "AddReceptors",
        "Parameters": "List[str]",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Assign receptors to this subarray
            Turn subarray to ObsState = IDLE if no
            receptor was previously assigned
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "ConfigureScan",
        "Parameters": "JSON str*",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Change observing state to READY
            Configure attributes from input JSON
            Subscribe events
            Configure VCC, VCC subarray, FSP, FSP Subarray
            Publish output links.
            See also :ref:`Configure Scan Sequence`
            """),   
        "Supported Interface(s)": supported_interfaces['configurescan'],
    },
    { 
        "Command": "EndScan",
        "Parameters": "None",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            End the scan
            """),   
        "Supported Interface(s)": '',
    },
    { 
        "Command": "ObsReset",
        "Parameters": "None",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Reset subarray scan configuration
            Keep assigned receptors
            Reset observing state to IDLE
            If in FAULT, send Abort/ObsReset to VCC
            If in FAULT, send Abort/ObsReset to
            FSP <function mode> subarrays
            No action on hardware
            See also :ref:`ObsReset Sequence`
            """    
        ),
        "Supported Interface(s)": "",
    },
    { 
        "Command": "RemoveAllReceptors",
        "Parameters": "None",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Remove all receptors
            Turn Subarray off if no receptors are
            assigned
            """),   
        "Supported Interface(s)": "",
    },
    { 
        "Command": "RemoveReceptors",
        "Parameters": "List[str]",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Remove receptors in input list
            Change observing state to EMPTY if no
            receptors assigned
            """),   
        "Supported Interface(s)": "",
    },
    { 
        "Command": "Restart",
        "Parameters": "None",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Reset subarray scan configuration
            Remove assigned receptors
            Restart observing state model to EMPTY
            If in FAULT, send Abort/ObsReset to VCC
            If in FAULT, send Abort/ObsReset to
            FSP <function mode> subarrays
            No action on hardware
            See also :ref:`Restart Sequence`
            """),   
        "Supported Interface(s)": "",
    },
    { 
        "Command": "Scan",
        "Parameters": "JSON str*",
        "Long Running Command": "Yes",
        "Return Type": "(ResultCode, str)",
        "Action": cleandoc(
            """
            Start scanning
            """),   
        "Supported Interface(s)": supported_interfaces['scan'],
    },
]

sub_table_commands = [
    { 
        "Command": "Delay Model",
        "Parameters": "JSON str*",
        "Long Running Command": "N/A",
        "Return Type": "None",
        "Action": cleandoc(
            """
            Pass DISH ID as VCC ID integer to FSPs and VCCs
            Update VCC Delay Model
            Update FSP Delay Model
            """),   
        "Supported Interface(s)": supported_interfaces["delaymodel"],
    },
]

table_data_mapping = {
    'Controller': controller_commands,
    'Subarray': subarray_commands,
    'Subscriptions': sub_table_commands,
}

class CommandTable(Directive):
    required_arguments = 1
    has_content = True

    def run(self):
        table_name = self.arguments[0]
        table_data = table_data_mapping[table_name]
        table = nodes.table()

        tgroup = nodes.tgroup(cols = 6)

        header = nodes.thead()
        header_row = nodes.row()

        for i in range(6):
            colspec_list = nodes.colspec(colwidth = 10)
            header_list = nodes.entry('', nodes.paragraph(text=HEADER_LIST[i]))
            header_row += header_list
            tgroup += colspec_list

        header  +=  (header_row)

        table_body = nodes.tbody()

        for index, command in enumerate(table_data):
            row_class = 'row-even' if index % 2 == 0 else 'row-odd'
            row = nodes.row("", classes=[row_class])
            row.append(nodes.entry('', nodes.paragraph(text=command['Command'])))
            row.append(nodes.entry('', nodes.paragraph(text=command['Parameters'])))
            row.append(nodes.entry('', nodes.paragraph(text=command['Long Running Command'])))
            row.append(nodes.entry('', nodes.paragraph(text=command['Return Type'])))
            action_entry = nodes.entry('')
            action_entry.append(self._parse_line_block(command['Action']))
            row.append(action_entry)
            supported_entry = nodes.entry('')
            if("https://schema.skao.int/ska-csp-configurescan/4.1" in command['Supported Interface(s)']):
                supported_entry.append(self._create_line_block_from_list(["https://schema.skao.int/ska-csp-configurescan/3.0"]))
            else:
                supported_entry.append(self._create_line_block_from_list(command['Supported Interface(s)']))
            row.append(supported_entry)
            table_body.append(row)

        table  +=  (tgroup)
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
    
