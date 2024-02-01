#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the FspPssSubarray component manager."""
from __future__ import annotations

import json
import os

import pytest
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.fsp.fsp_pss_subarray_component_manager import (
    FspPssSubarrayComponentManager,
)
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockCallable

file_path = os.path.dirname(os.path.abspath(__file__))


class TestFspPssSubarrayComponentManager:
    """Tests of the fsp pss subarray component manager."""

    def test_communication(
        self: TestFspPssSubarrayComponentManager,
        fsp_pss_subarray_component_manager: FspPssSubarrayComponentManager,
        communication_status_changed_callback: MockCallable,
    ) -> None:
        """
        Test the fsp pss subarray component manager's management of communication.

        :param fsp_pss_subarray_component_manager: the fsp pss subarray component
            manager under test.
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        """
        assert (
            fsp_pss_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        fsp_pss_subarray_component_manager.start_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.NOT_ESTABLISHED
        )
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.ESTABLISHED
        )
        assert (
            fsp_pss_subarray_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )

        fsp_pss_subarray_component_manager.stop_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.DISABLED
        )
        assert (
            fsp_pss_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

    @pytest.mark.parametrize(
        "config_file_name",
        [("/../../data/FspPssSubarray_ConfigureScan_basic.json")],
    )
    def test_configure_scan(
        self: TestFspPssSubarrayComponentManager,
        fsp_pss_subarray_component_manager: FspPssSubarrayComponentManager,
        config_file_name: str,
    ) -> None:
        """
        Test the fsp pss subarray component manager's configure_scan command.

        :param fsp_pss_subarray_component_manager: the fsp pss subarray component
            manager under test.
        :param config_file_name: the name of the configuration file
        """
        assert (
            fsp_pss_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        fsp_pss_subarray_component_manager.start_communicating()

        assert fsp_pss_subarray_component_manager.receptors == []
        assert fsp_pss_subarray_component_manager.search_beams == []
        assert fsp_pss_subarray_component_manager.search_window_id == 0
        assert fsp_pss_subarray_component_manager.search_beam_id == []
        assert fsp_pss_subarray_component_manager.output_enable == 0

        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        configuration = json.loads(json_str)
        fsp_pss_subarray_component_manager.configure_scan(json_str)
        f.close()

        assert (
            fsp_pss_subarray_component_manager.fsp_id
            == configuration["fsp_id"]
        )
        assert fsp_pss_subarray_component_manager.search_window_id == int(
            configuration["search_window_id"]
        )
        for i, searchBeam in enumerate(configuration["search_beam"]):
            assert fsp_pss_subarray_component_manager.search_beams[
                i
            ] == json.dumps(searchBeam)
            assert fsp_pss_subarray_component_manager.search_beam_id[i] == int(
                searchBeam["search_beam_id"]
            )
        # TODO verify added receptors

    @pytest.mark.parametrize("scan_id", [1, 2])
    def test_scan(
        self: TestFspPssSubarrayComponentManager,
        fsp_pss_subarray_component_manager: FspPssSubarrayComponentManager,
        scan_id: int,
    ) -> None:
        """
        Test the fsp pss subarray component manager's scan command.

        :param fsp_pss_subarray_component_manager: the fsp pss subarray component
            manager under test.
        :param scan_id: the scan id
        """

        assert (
            fsp_pss_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        fsp_pss_subarray_component_manager.start_communicating()

        fsp_pss_subarray_component_manager.scan(scan_id)
        assert fsp_pss_subarray_component_manager.scan_id == scan_id

    def test_abort_obs_reset(
        self: TestFspPssSubarrayComponentManager,
        fsp_pss_subarray_component_manager: FspPssSubarrayComponentManager,
    ) -> None:
        """
        Test the fsp pss subarray component manager's Abort and Reset commands. If ran in isolation, tests from idle state.

        :param fsp_pss_subarray_component_manager: the fsp pss subarray component
            manager under test.
        """

        (result_code, _) = fsp_pss_subarray_component_manager.abort()
        assert result_code == ResultCode.OK

        (result_code, _) = fsp_pss_subarray_component_manager.obsreset()
        assert result_code == ResultCode.OK

        assert fsp_pss_subarray_component_manager._search_beams == []
        assert fsp_pss_subarray_component_manager._search_window_id == 0
        assert fsp_pss_subarray_component_manager._search_beam_id == []
        assert fsp_pss_subarray_component_manager._output_enable == 0
        assert fsp_pss_subarray_component_manager.scan_id == 0
        assert fsp_pss_subarray_component_manager._config_id == ""
        assert fsp_pss_subarray_component_manager._receptors == []

    @pytest.mark.parametrize(
        "config_file_name",
        [("/../../data/FspPssSubarray_ConfigureScan_basic.json")],
    )
    def test_abort_from_ready_obs_reset(
        self: TestFspPssSubarrayComponentManager,
        fsp_pss_subarray_component_manager: FspPssSubarrayComponentManager,
        config_file_name: str,
    ) -> None:
        """
        Test the fsp pss subarray component manager's Abort and Reset commands from ready state.

        :param fsp_pss_subarray_component_manager: the fsp pss subarray component manager under test.
        :param config_file_name: the name of the configuration file
        """

        self.test_configure_scan(
            fsp_pss_subarray_component_manager, config_file_name
        )
        self.test_abort_obs_reset(fsp_pss_subarray_component_manager)

    @pytest.mark.parametrize(
        "config_file_name",
        [("/../../data/FspPssSubarray_ConfigureScan_basic.json")],
    )
    def test_abort_from_scanning_obs_reset(
        self: TestFspPssSubarrayComponentManager,
        fsp_pss_subarray_component_manager: FspPssSubarrayComponentManager,
        config_file_name: str,
    ) -> None:
        """
        Test the fsp pss subarray component manager's Abort and Reset commands from scanning state.

        :param fsp_pss_subarray_component_manager: the fsp pss subarray component manager under test.
        :param config_file_name: the name of the configuration file
        """

        self.test_scan(fsp_pss_subarray_component_manager, config_file_name)
        self.test_abort_obs_reset(fsp_pss_subarray_component_manager)
