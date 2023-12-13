#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the SLIM component manager."""
from __future__ import annotations

import os

import pytest
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.slim.slim_component_manager import SlimComponentManager
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockCallable

file_path = os.path.dirname(os.path.abspath(__file__))


class TestSlimComponentManager:
    """Tests of the SLIM component manager."""

    def test_communication(
        self: TestSlimComponentManager,
        slim_component_manager: SlimComponentManager,
        communication_status_changed_callback: MockCallable,
    ) -> None:
        """
        Test the SLIM component manager's management of communication.

        :param slim_component_manager: the SLIM component
            manager under test.
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        """
        assert (
            slim_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        slim_component_manager.start_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.NOT_ESTABLISHED
        )
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.ESTABLISHED
        )
        assert (
            slim_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )

        slim_component_manager.stop_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.DISABLED
        )
        assert (
            slim_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

    @pytest.mark.parametrize(
        "mesh_config_filename",
        [("./mnt/slim/fs_slim_config.yaml")],
    )
    def test_configure(
        self: TestSlimComponentManager,
        slim_component_manager: SlimComponentManager,
        mesh_config_filename: str,
    ) -> None:
        """
        Test the SLIM component manager's connect_tx_rx command.

        :param slim_component_manager: the SLIM component
            manager under test.
        :param mesh_config_filename: name of SLIM configuration YAML file.
        """
        assert (
            slim_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        slim_component_manager.start_communicating()
        with open(mesh_config_filename, "r") as mesh_config:
            result = slim_component_manager.configure(mesh_config.read())
            assert result[0] == ResultCode.OK
