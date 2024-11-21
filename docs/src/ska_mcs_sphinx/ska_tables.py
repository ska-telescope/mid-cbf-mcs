# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2024 National Research Council of Canada

from docutils import nodes
from docutils.statemachine import ViewList
from docutils.parsers.rst import Directive
from sphinx.util.nodes import nested_parse_with_titles

# import table data
import ska_mcs_sphinx.table_data as table_data

table_data_mapping = {
    'Supported_Validation': table_data.configurescan_validation_rules_data,
    'Controller': table_data.controller_commands_data,
    'Subarray': table_data.subarray_commands_data,
    'Subscriptions': table_data.subscription_commands_data
}

class CommandTable(Directive):
    required_arguments = 1
    has_content = True

    def run(self):
        table_name = self.arguments[0]
        table_data :list[dict] = table_data_mapping[table_name]["data"]
        headers_data = table_data_mapping[table_name]["headers"]
        table = nodes.table()
        tgroup = nodes.tgroup(cols = len(headers_data))

        header = nodes.thead()
        header_row = nodes.row()

        for header_value in headers_data:
            colspec_list = nodes.colspec(colwidth = 10)
            header_list = nodes.entry('', nodes.paragraph(text=header_value))
            header_row += header_list
            tgroup += colspec_list

        header  +=  (header_row)

        table_body = nodes.tbody()

        for index, row_data in enumerate(table_data):
            row_class = 'row-even' if index % 2 == 0 else 'row-odd'
            row = nodes.row("", classes=[row_class])
            for header_value in headers_data:
                col_data = row_data.get(header_value,'')
                # Special cases for some column names
                if header_value == 'Action':
                    action_entry = nodes.entry('')
                    action_entry.append(self._parse_line_block(col_data))
                    row.append(action_entry)
                elif header_value == 'Supported Interface(s)':
                    supported_entry = nodes.entry('')
                    supported_entry.append(self._create_line_block_from_list(col_data))
                    row.append(supported_entry)
                else:
                    col_entry = nodes.entry()
                    col_entry.children = self._parse_text(col_data)
                    row.append(col_entry)

            table_body.append(row)

        table   +=  (tgroup)
        tgroup  +=  (header)
        tgroup  +=  (table_body)
        return [table]

    def _parse_text(self, text_to_parse: str):
        lines = text_to_parse.split('\n')
        view_list_to_parse = ViewList()
        for index, line in enumerate(lines):
            # Need to provide a source to report in warnings
            view_list_to_parse.append(line, 
                                      source="ska_mcs_sphinx.ska_tables",
                                      offset=index)
        # Create a node.
        node = nodes.section()
        node.document = self.state.document
        
        nested_parse_with_titles(self.state, view_list_to_parse, node)
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
