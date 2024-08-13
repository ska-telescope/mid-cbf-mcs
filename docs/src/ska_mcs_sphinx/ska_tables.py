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

import importlib


# Variables: num_rows, command_list, param_list, return_list, action_list, supported_versions_list
# TODO: For supported versions we can read param list and if json is found we can
#       look for command with matching prefix as supported versions

class SkaTables(Directive):
    # required_arguments = 5
    has_content = True


    def run(self):

        table = nodes.table()

        tgroup = nodes.tgroup(cols = 5)
        colspec = nodes.colspec()           # Why needed?
        header = nodes.thead()              # Need variable or can just call?
        header_row = nodes.row()
        header_1 = nodes.entry("Command")
        header_2 = nodes.entry("Parameters")
        header_3 = nodes.entry("Return type")
        header_4 = nodes.entry("Action")
        header_5 = nodes.entry("Supported versions")
        header_row.append(header_1)
        header_row.append(header_2)
        header_row.append(header_3)
        header_row.append(header_4)
        header_row.append(header_5)

        header.append(header_row)       # Assume this is right


        table_body = nodes.tbody()

        row1 = nodes.row()
        r1_c1_entry = nodes.entry("Off")
        r1_c2_entry = nodes.entry("None")
        r1_c3_entry = nodes.entry("None")
        r1_c4_entry = nodes.entry("(ResultCode, str)")
        r1_c5_entry = nodes.entry("Set power state to OFF for controller and \
                                    subordinate devices (subarrays, VCCs, FSPs)\
                                    Turn off power to all hardware\
                                    See also :ref:'Off Sequence'")          # Test if this works in rst
        row1.append(r1_c1_entry)
        row1.append(r1_c2_entry)
        row1.append(r1_c3_entry)
        row1.append(r1_c4_entry)
        row1.append(r1_c5_entry)

        table_body.append(row1)

        table.append(tgroup)
        tgroup.append(colspec)
        tgroup.append(header)
        tgroup.append(table_body)
        table.append(tgroup)

        return [table]


class HelloDirective(Directive):
    """A directive to say hello!"""


    def run(self) -> list[nodes.Node]:
        table = nodes.table()
        groups = nodes.table(cols = 2)
        colspec_1 = nodes.colspec(colwidth = 8)
        colspec_2 = nodes.colspec(colwidth = 4)
        body = nodes.tbody()
        row_1 = nodes.row()
        r1_c1 = nodes.entry(nodes.paragraph("bread"))
        r1_c2 = nodes.entry(nodes.paragraph("E2"))
        row_2 = nodes.row()
        r2_c1 = nodes.entry(nodes.paragraph("butter"))
        r2_c2 = nodes.entry(nodes.paragraph("E30"))

        row_2.append(r2_c1)
        row_2.append(r2_c2)

        row_1.append(r1_c1)
        row_1.append(r1_c2)

        body.append(row_1)
        body.append(row_2)

        groups.append(colspec_1)
        groups.append(colspec_2)
        groups.append(body)

        table.append(groups)
        return [table]

        





