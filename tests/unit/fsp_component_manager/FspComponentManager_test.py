#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the Fsp component manager."""
from __future__ import annotations

import os
from typing import List

import pytest
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.commons.global_enum import FspModes
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.fsp.fsp_component_manager import FspComponentManager
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockCallable

file_path = os.path.dirname(os.path.abspath(__file__))


class TestFspComponentManager:
    """Tests of the Fsp component manager."""

    def test_communication(
        self: TestFspComponentManager,
        fsp_component_manager: FspComponentManager,
        communication_status_changed_callback: MockCallable,
    ) -> None:
        """
        Test the fsp component manager's management of communication.

        :param fsp_component_manager: the fsp component
            manager under test.
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        """
        assert (
            fsp_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        fsp_component_manager.start_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.NOT_ESTABLISHED
        )
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.ESTABLISHED
        )
        assert (
            fsp_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )

        fsp_component_manager.stop_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.DISABLED
        )
        assert (
            fsp_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

    @pytest.mark.parametrize("command", ["On", "Off", "Standby"])
    def test_Power_Commands(
        self: TestFspComponentManager,
        fsp_component_manager: FspComponentManager,
        command: str,
    ) -> None:
        """
        Test the On/Off/Standby Commands

        :param fsp_component_manager: the fsp component
            manager under test.
        :param command: the command to test (one of On/Off/Standby)
        """
        fsp_component_manager.start_communicating()
        assert (
            fsp_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert fsp_component_manager._connected is True

        if command == "On":
            (result_code, msg) = fsp_component_manager.on()
            assert (result_code, msg) == (
                ResultCode.OK,
                "Fsp On command completed OK",
            )
        elif command == "Off":
            (result_code, msg) = fsp_component_manager.off()
            assert (result_code, msg) == (
                ResultCode.OK,
                "Fsp Off command completed OK",
            )
        elif command == "Standby":
            (result_code, msg) = fsp_component_manager.standby()
            assert (result_code, msg) == (
                ResultCode.OK,
                "Fsp Standby command completed OK",
            )

    @pytest.mark.parametrize("sub_ids", [([3, 4, 15]), ([1])])
    def test_AddRemoveSubarrayMembership(
        self: TestFspComponentManager,
        fsp_component_manager: FspComponentManager,
        sub_ids: List[int],
    ) -> None:
        """
        Test Fsp's AddSubarrayMembership and
        RemoveSubarrayMembership commands

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param sub_ids: list of subarray ids
        """

        fsp_component_manager.start_communicating()
        assert (
            fsp_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert fsp_component_manager._connected is True

        # subarray membership should be empty
        assert fsp_component_manager.subarray_membership == []

        # add fsp to all but last test subarray
        for sub_id in sub_ids[:-1]:
            fsp_component_manager.add_subarray_membership(sub_id)
        for idx, sub_id in enumerate(sub_ids[:-1]):
            assert (
                list(fsp_component_manager.subarray_membership)[idx]
                == sub_ids[:-1][idx]
            )

        # remove fsp from first test subarray
        fsp_component_manager.remove_subarray_membership(sub_ids[0])
        for idx, sub_id in enumerate(sub_ids[1:-1]):
            assert (
                list(fsp_component_manager.subarray_membership)[idx]
                == sub_ids[1:-1][idx]
            )

        # add fsp to last test subarray
        fsp_component_manager.add_subarray_membership(sub_ids[-1])
        for idx, sub_id in enumerate(sub_ids[1:]):
            assert (
                list(fsp_component_manager.subarray_membership)[idx]
                == sub_ids[1:][idx]
            )

        # remove fsp from all subarrays
        for sub_id in sub_ids:
            fsp_component_manager.remove_subarray_membership(sub_id)
        assert fsp_component_manager.subarray_membership == []

    @pytest.mark.parametrize(
        "jones_matrix_file_name, \
        sub_id",
        [("/../../data/jonesmatrix_unit_test.json", 1)],
    )
    def test_UpdateJonesMatrix(
        self: TestFspComponentManager,
        fsp_component_manager: FspComponentManager,
        jones_matrix_file_name: str,
        sub_id: int,
    ) -> None:
        """
        Test Fsp's UpdateJonesMatrix command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param jones_matrix_file_name: JSON file for the jones matrix
        :param sub_id: the subarray id
        """

        fsp_component_manager.start_communicating()
        assert (
            fsp_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert fsp_component_manager._connected is True

        # on invoked to get capability proxy
        (result_code, msg) = fsp_component_manager.on()
        assert (result_code, msg) == (
            ResultCode.OK,
            "Fsp On command completed OK",
        )

        fsp_component_manager.add_subarray_membership(sub_id)
        assert list(fsp_component_manager.subarray_membership) == [sub_id]

        # jones matrix values should be set to "" after init
        assert fsp_component_manager.jones_matrix == ""

        # read the json file
        f = open(file_path + jones_matrix_file_name)
        jones_matrix = f.read().replace("\n", "")
        f.close()

        valid_function_modes = ["PSS-BF", "PST-BF", "VLBI"]
        for mode in valid_function_modes:
            fsp_component_manager.set_function_mode(mode)
            if mode == "PSS-BF":
                assert (
                    fsp_component_manager.function_mode
                    == FspModes.PSS_BF.value
                )
            elif mode == "PST-BF":
                assert (
                    fsp_component_manager.function_mode
                    == FspModes.PST_BF.value
                )
            elif mode == "VLBI":
                assert (
                    fsp_component_manager.function_mode == FspModes.VLBI.value
                )

            fsp_component_manager.update_jones_matrix(jones_matrix)

            # verify the Jones Matrix was updated successfully
            assert jones_matrix == fsp_component_manager.jones_matrix

    @pytest.mark.parametrize(
        "delay_model_file_name, \
        sub_id",
        [("/../../data/delaymodel_unit_test.json", 1)],
    )
    def test_UpdateDelayModel(
        self: TestFspComponentManager,
        fsp_component_manager: FspComponentManager,
        delay_model_file_name: str,
        sub_id: int,
    ) -> None:
        """
        Test Fsp's UpdateDelayModel command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param delay_model_file_name: JSON file for the delay model
        :param sub_id: the subarray id
        """

        fsp_component_manager.start_communicating()
        assert (
            fsp_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert fsp_component_manager._connected is True

        # on invoked to get capability proxy
        (result_code, msg) = fsp_component_manager.on()
        assert (result_code, msg) == (
            ResultCode.OK,
            "Fsp On command completed OK",
        )

        fsp_component_manager.add_subarray_membership(sub_id)
        assert list(fsp_component_manager.subarray_membership) == [sub_id]

        # delay model should be empty string after init
        assert fsp_component_manager.delay_model == ""

        # read the json file
        f = open(file_path + delay_model_file_name)
        delay_model = f.read().replace("\n", "")
        f.close()

        valid_function_modes = ["PSS-BF", "PST-BF", "CORR"]
        for mode in valid_function_modes:
            fsp_component_manager.set_function_mode(mode)
            if mode == "PSS-BF":
                assert (
                    fsp_component_manager.function_mode
                    == FspModes.PSS_BF.value
                )
            elif mode == "PST-BF":
                assert (
                    fsp_component_manager.function_mode
                    == FspModes.PST_BF.value
                )
            elif mode == "CORR":
                assert (
                    fsp_component_manager.function_mode == FspModes.CORR.value
                )

            fsp_component_manager.update_delay_model(delay_model)

            # verify the delay model was updated successfully
            assert delay_model == fsp_component_manager.delay_model

    @pytest.mark.parametrize(
        "timing_beam_weights_file_name, \
         sub_id",
        [("/../../data/timingbeamweights_fsp_unit_test.json", 1)],
    )
    def test_UpdateBeamWeights(
        self: TestFspComponentManager,
        fsp_component_manager: FspComponentManager,
        timing_beam_weights_file_name: str,
        sub_id: int,
    ) -> None:
        """
        Test Fsp's UpdateBeamWeights command

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        :param timing_beam_weights_file_name: JSON file for the timing beam weights
        :param sub_id: the subarray id
        """

        fsp_component_manager.start_communicating()
        assert (
            fsp_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert fsp_component_manager._connected is True

        # on invoked to get capability proxy
        (result_code, msg) = fsp_component_manager.on()
        assert (result_code, msg) == (
            ResultCode.OK,
            "Fsp On command completed OK",
        )

        fsp_component_manager.add_subarray_membership(sub_id)
        assert list(fsp_component_manager.subarray_membership) == [sub_id]

        # timing beam weights should be set to "" after init
        assert fsp_component_manager.timing_beam_weights == ""

        # update only valid for function mode PST-BF
        fsp_component_manager.set_function_mode("PST-BF")
        assert fsp_component_manager.function_mode == FspModes.PST_BF.value

        # read the json file
        f = open(file_path + timing_beam_weights_file_name)
        timing_beam_weights = f.read().replace("\n", "")
        f.close()

        # update the weights
        fsp_component_manager.update_timing_beam_weights(timing_beam_weights)

        # verify the timing beam weights were updated successfully
        assert timing_beam_weights == fsp_component_manager.timing_beam_weights
