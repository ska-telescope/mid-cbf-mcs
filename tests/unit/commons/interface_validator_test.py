#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfController."""

from __future__ import annotations

# SKA imports
from ska_mid_cbf_mcs.commons.validate_interface import validate_interface

input_txt = """
            hello
            """

input_no_key = """
                {
                "scan_id": 7,
                "transaction_id": "txn-....-00001"
                }
                """

input_not_string = """
                {
                "interface": 5,
                "scan_id": 1,
                "transaction_id": "txn-....-00001"
                }
                """

input_configscan_supported = """
                {
                "interface": "https://schema.skao.int/ska-csp-configurescan/4.1",
                "scan_id": 1,
                "transaction_id": "txn-....-00001"
                }
                """

input_configscan_unsupported = """
                {
                "interface": "https://schema.skao.int/ska-csp-configurescan/23.0",
                "scan_id": 1,
                "transaction_id": "txn-....-00001"
                }
                """

input_scan_supported = """
                {
                "interface": "https://schema.skao.int/ska-csp-scan/2.3",
                "scan_id": 1,
                "transaction_id": "txn-....-00001"
                }
                """

input_scan_unsupported = """
                {
                "interface": "https://schema.skao.int/ska-csp-scan/23.0",
                "scan_id": 1,
                "transaction_id": "txn-....-00001"
                }
                """

input_initsysparam_supported = """
                {
                "interface": "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0",
                "scan_id": 1,
                "transaction_id": "txn-....-00001"
                }
                """

input_initsysparam_unsupported = """
                {
                "interface": "https://schema.skao.int/ska-mid-cbf-initsysparam/23.0",
                "scan_id": 1,
                "transaction_id": "txn-....-00001"
                }
                """

input_delaymodel_supported = """
                {
                "interface": "https://schema.skao.int/ska-mid-csp-delaymodel/3.0",
                "scan_id": 1,
                "transaction_id": "txn-....-00001"
                }
                """

input_delaymodel_unsupported = """
                {
                "interface": "https://schema.skao.int/ska-mid-csp-delaymodel/23.0",
                "scan_id": 1,
                "transaction_id": "txn-....-00001"
                }
                """

input_lowconfigscan = """
                {
                "interface": "https://schema.skao.int/ska-low-cbf-configurescan/1.0",
                "scan_id": 1,
                "transaction_id": "txn-....-00001"
                }
                """


class TestInterfaceValidator:
    """
    Test class for interface validation tests.
    """

    def test_UnsupportedJSON(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test input that is not a valid JSON string
        """
        assert validate_interface(input_txt, "scan") == (
            False,
            "The command parameters could not be parsed",
        )

    def test_MissingInterfaceKey(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test input without "interface" key
        """
        assert validate_interface(input_no_key, "scan") == (
            False,
            "The command is missing the required interface parameter",
        )

    def test_NonStringInterface(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test non-string interface value
        """
        assert validate_interface(input_not_string, "scan") == (
            False,
            "The value retrieved from the interface key is not a string",
        )

    def test_IncorrectCommand(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test mismatched interface and command
        """
        assert validate_interface(input_configscan_supported, "scan") == (
            False,
            "Interface 'https://schema.skao.int/ska-csp-configurescan/4.1' not supported for command 'scan'",
        )

    def test_SupportedConfigureScan(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test configure scan
        """
        assert validate_interface(
            input_configscan_supported, "configurescan"
        ) == (True, "")

    def test_UnsupportedConfigureScan(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test configure scan with unsupported interface
        """
        assert validate_interface(
            input_configscan_unsupported, "configurescan"
        ) == (
            False,
            "Interface 'https://schema.skao.int/ska-csp-configurescan/23.0' not supported for command 'configurescan'",
        )

    def test_SupportedScan(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test scan
        """
        assert validate_interface(input_scan_supported, "scan") == (True, "")

    def test_UnsupportedScan(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test scan with unsupported interface
        """
        assert validate_interface(input_scan_unsupported, "scan") == (
            False,
            "Interface 'https://schema.skao.int/ska-csp-scan/23.0' not supported for command 'scan'",
        )

    def test_SupportedInitSysParam(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test initsysparam
        """
        assert validate_interface(
            input_initsysparam_supported, "initsysparam"
        ) == (True, "")

    def test_UnsupportedInitSysParam(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test initsysparam with unsupported interface
        """
        assert validate_interface(
            input_initsysparam_unsupported, "initsysparam"
        ) == (
            False,
            "Interface 'https://schema.skao.int/ska-mid-cbf-initsysparam/23.0' not supported for command 'initsysparam'",
        )

    def test_SupportedDelayModel(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test delay model
        """
        assert validate_interface(
            input_delaymodel_supported, "delaymodel"
        ) == (True, "")

    def test_UnsupportedDelayModel(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test delay model with unsupported interface
        """
        assert validate_interface(
            input_delaymodel_unsupported, "delaymodel"
        ) == (
            False,
            "Interface 'https://schema.skao.int/ska-mid-csp-delaymodel/23.0' not supported for command 'delaymodel'",
        )

    def test_LowConfigScan(
        self: TestInterfaceValidator,
    ) -> None:
        """
        Test low config scan
        """
        assert validate_interface(input_lowconfigscan, "configure") == (
            False,
            "Interface 'https://schema.skao.int/ska-low-cbf-configurescan/1.0' not supported for command 'configure'",
        )
