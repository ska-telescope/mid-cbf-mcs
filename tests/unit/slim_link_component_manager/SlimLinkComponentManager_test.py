#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the SlimLink component manager."""
from __future__ import annotations

import os

import pytest
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.slim.slim_link_component_manager import (
    SlimLinkComponentManager,
)
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockCallable

file_path = os.path.dirname(os.path.abspath(__file__))


class TestSlimLinkComponentManager:
    """Tests of the SlimLink component manager."""

    def test_communication(
        self: TestSlimLinkComponentManager,
        slim_link_component_manager: SlimLinkComponentManager,
        communication_status_changed_callback: MockCallable,
    ) -> None:
        """
        Test the SlimLink component manager's management of communication.

        :param slim_link_component_manager: the SlimLink component
            manager under test.
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        """
        assert (
            slim_link_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        slim_link_component_manager.start_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.NOT_ESTABLISHED
        )
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.ESTABLISHED
        )
        assert (
            slim_link_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )

        slim_link_component_manager.stop_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.DISABLED
        )
        assert (
            slim_link_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

    @pytest.mark.parametrize(
        "tx_name, \
        rx_name",
        [("mid_csp_cbf/slim-tx-rx/tx-test", "mid_csp_cbf/slim-tx-rx/rx-test")],
    )
    def test_connect_tx_rx(
        self: TestSlimLinkComponentManager,
        slim_link_component_manager: SlimLinkComponentManager,
        tx_name: str,
        rx_name: str,
    ) -> None:
        """
        Test the SlimLink component manager's connect_tx_rx command.

        :param slim_link_component_manager: the SlimLink component
            manager under test.
        :param tx_name: FQDN of the SLIM-tx mock device
        :param rx_name: FQDN of the SLIM-rx mock device
        """
        assert (
            slim_link_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        slim_link_component_manager.start_communicating()

        assert slim_link_component_manager.tx_device_name == ""
        assert slim_link_component_manager.tx_device_name == ""

        slim_link_component_manager.tx_device_name = tx_name
        slim_link_component_manager.rx_device_name = rx_name

        result = slim_link_component_manager.connect_slim_tx_rx()
        assert result[0] == ResultCode.OK

    def test_verify_connection(
        self: TestSlimLinkComponentManager,
        slim_link_component_manager: SlimLinkComponentManager,
    ) -> None:
        """
        Test the SlimLink component manager's verify_connection command.

        :param slim_link_component_manager: the SlimLink component
            manager under test.
        """
        assert (
            slim_link_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        self.test_connect_tx_rx(
            slim_link_component_manager,
            "mid_csp_cbf/slim-tx-rx/tx-test",
            "mid_csp_cbf/slim-tx-rx/rx-test",
        )

        result = slim_link_component_manager.verify_connection()
        assert result[0] == ResultCode.OK

    def test_disconnect_tx_rx(
        self: TestSlimLinkComponentManager,
        slim_link_component_manager: SlimLinkComponentManager,
    ) -> None:
        """
        Test the SlimLink component manager's disconnect_tx_rx command.

        :param slim_link_component_manager: the SlimLink component
            manager under test.
        """
        assert (
            slim_link_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        self.test_connect_tx_rx(
            slim_link_component_manager,
            "mid_csp_cbf/slim-tx-rx/tx-test",
            "mid_csp_cbf/slim-tx-rx/rx-test",
        )

        result = slim_link_component_manager.disconnect_slim_tx_rx()
        assert result[0] == ResultCode.OK

    def test_clear_counters(
        self: TestSlimLinkComponentManager,
        slim_link_component_manager: SlimLinkComponentManager,
    ) -> None:
        """
        Test the SlimLink component manager's clear_counters command.

        :param slim_link_component_manager: the SlimLink component
            manager under test.
        """
        assert (
            slim_link_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        self.test_connect_tx_rx(
            slim_link_component_manager,
            "mid_csp_cbf/slim-tx-rx/tx-test",
            "mid_csp_cbf/slim-tx-rx/rx-test",
        )

        result = slim_link_component_manager.clear_counters()
        assert result[0] == ResultCode.OK