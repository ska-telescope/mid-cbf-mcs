#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the FspCorrSubarray component manager."""
from __future__ import annotations

import json
import logging
import os

import pytest

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.fsp.fsp_corr_subarray_component_manager import (
    FspCorrSubarrayComponentManager,
)
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockCallable

file_path = os.path.dirname(os.path.abspath(__file__))


class TestFspCorrSubarrayComponentManager:
    """Tests of the fsp corr subarray component manager."""

    def test_communication(
        self: TestFspCorrSubarrayComponentManager,
        fsp_corr_subarray_component_manager: FspCorrSubarrayComponentManager,
        communication_status_changed_callback: MockCallable,
    ) -> None:
        """
        Test the fsp corr subarray component manager's management of communication.

        :param fsp_corr_subarray_component_manager: the fsp corr subarray component
            manager under test.
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        """
        assert (
            fsp_corr_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        fsp_corr_subarray_component_manager.start_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.NOT_ESTABLISHED
        )
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.ESTABLISHED
        )
        assert (
            fsp_corr_subarray_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )

        fsp_corr_subarray_component_manager.stop_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.DISABLED
        )
        assert (
            fsp_corr_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

    @pytest.mark.parametrize(
        "config_file_name",
        [("/../../data/FspCorrSubarray_ConfigureScan_basic.json")],
    )
    def test_configure_scan(
        self: TestFspCorrSubarrayComponentManager,
        fsp_corr_subarray_component_manager: FspCorrSubarrayComponentManager,
        config_file_name: str,
    ) -> None:
        """
        Test the fsp corr subarray component manager's configure_scan command.

        :param fsp_corr_subarray_component_manager: the fsp corr subarray component
            manager under test.
        :param config_file_name: the name of the configuration file
        """
        assert (
            fsp_corr_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        fsp_corr_subarray_component_manager.start_communicating()

        assert fsp_corr_subarray_component_manager.receptors == []
        assert fsp_corr_subarray_component_manager.frequency_band == 0
        assert [
            fsp_corr_subarray_component_manager.stream_tuning[0],
            fsp_corr_subarray_component_manager.stream_tuning[1],
        ] == [0, 0]
        assert (
            fsp_corr_subarray_component_manager.frequency_band_offset_stream_1
            == 0
        )
        assert (
            fsp_corr_subarray_component_manager.frequency_band_offset_stream_2
            == 0
        )
        assert fsp_corr_subarray_component_manager.frequency_slice_id == 0
        assert fsp_corr_subarray_component_manager.bandwidth == 0
        assert fsp_corr_subarray_component_manager.zoom_window_tuning == 0
        assert fsp_corr_subarray_component_manager.integration_factor == 0
        assert fsp_corr_subarray_component_manager.scan_id == 0
        assert fsp_corr_subarray_component_manager.config_id == ""
        for i in range(const.NUM_CHANNEL_GROUPS):
            assert (
                fsp_corr_subarray_component_manager.channel_averaging_map[i][0]
                == int(i * const.NUM_FINE_CHANNELS / const.NUM_CHANNEL_GROUPS)
                + 1
            )
            assert (
                fsp_corr_subarray_component_manager.channel_averaging_map[i][1]
                == 0
            )
        assert fsp_corr_subarray_component_manager.vis_destination_address == {
            "outputHost": [],
            "outputMac": [],
            "outputPort": [],
        }
        assert fsp_corr_subarray_component_manager.fsp_channel_offset == 0
        for i in range(40):
            for j in range(2):
                assert (
                    fsp_corr_subarray_component_manager.output_link_map[i][j]
                    == 0
                )

        # run ConfigureScan
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        configuration = json.loads(json_str)
        fsp_corr_subarray_component_manager.configure_scan(json_str)
        f.close()

        # verify correct attribute values are received
        for idx, receptorID in enumerate(
            fsp_corr_subarray_component_manager.receptors
        ):
            assert receptorID == configuration["receptor_ids"][idx][1]
        assert (
            fsp_corr_subarray_component_manager.frequency_band
            == freq_band_dict()[configuration["frequency_band"]]["band_index"]
        )
        assert (
            fsp_corr_subarray_component_manager.frequency_slice_id
            == configuration["frequency_slice_id"]
        )
        if "band_5_tuning" in configuration:
            if fsp_corr_subarray_component_manager.frequency_band in [4, 5]:
                band5Tuning_config = configuration["band_5_tuning"]
                for i in range(0, len(band5Tuning_config)):
                    assert (
                        fsp_corr_subarray_component_manager.stream_tuning[i]
                        == band5Tuning_config[i]
                    )
        else:
            logging.info("Attribute band5Tuning not in configuration")

        assert (
            fsp_corr_subarray_component_manager.zoom_window_tuning
            == configuration["zoom_window_tuning"]
        )
        assert (
            fsp_corr_subarray_component_manager.integration_factor
            == configuration["integration_factor"]
        )
        channelAveragingMap_config = configuration["channel_averaging_map"]
        logging.info(channelAveragingMap_config)
        for i, chan in enumerate(channelAveragingMap_config):
            for j in range(0, len(chan)):
                assert (
                    fsp_corr_subarray_component_manager.channel_averaging_map[
                        i
                    ][j]
                    == channelAveragingMap_config[i][j]
                )

    @pytest.mark.parametrize(
        "config_file_name, scan_id",
        [
            ("/../../data/FspCorrSubarray_ConfigureScan_basic.json", 1),
            ("/../../data/FspCorrSubarray_ConfigureScan_basic.json", 2),
        ],
    )
    def test_scan(
        self: TestFspCorrSubarrayComponentManager,
        fsp_corr_subarray_component_manager: FspCorrSubarrayComponentManager,
        config_file_name: str,
        scan_id: int,
    ) -> None:
        """
        Test the fsp corr subarray component manager's scan command.

        :param fsp_corr_subarray_component_manager: the fsp corr subarray component
            manager under test.
        :param scan_id: the scan id
        """

        assert (
            fsp_corr_subarray_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        fsp_corr_subarray_component_manager.start_communicating()

        # run ConfigureScan to get capability proxies
        f = open(file_path + config_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        fsp_corr_subarray_component_manager.configure_scan(json_str)

        fsp_corr_subarray_component_manager.scan(scan_id)
        assert fsp_corr_subarray_component_manager.scan_id == scan_id
