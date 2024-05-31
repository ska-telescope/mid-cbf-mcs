#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the CbfController component manager."""
from __future__ import annotations

# Path
import os

from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.controller.controller_component_manager import (
    ControllerComponentManager,
)
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockCallable

json_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


class TestControllerComponentManager:
    """Tests of the controller component manager."""

    def test_communication(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
        communication_status_changed_callback: MockCallable,
    ) -> None:
        """
        Test the controller component manager's management of communication.

        :param controller_component_manager: the controller component
            manager under test.
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        """
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

        controller_component_manager.start_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.NOT_ESTABLISHED
        )
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.ESTABLISHED
        )
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )

        controller_component_manager.stop_communicating()
        communication_status_changed_callback.assert_next_call(
            CommunicationStatus.DISABLED
        )
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.DISABLED
        )

    def test_On(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test on().
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        with open(json_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(sp)
        assert result_code == ResultCode.OK

        (result_code, _) = controller_component_manager.on()
        assert result_code == ResultCode.OK

    def test_On_No_SysParam(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test on().
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        (result_code, _) = controller_component_manager.on()
        assert result_code == ResultCode.FAILED

    def test_Off(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test off().
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        with open(json_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(sp)
        assert result_code == ResultCode.OK

        (result_code, _) = controller_component_manager.on()

        (result_code, _) = controller_component_manager.off()
        assert result_code == ResultCode.OK

    def test_Standby(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test standby().
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        (result_code, _) = controller_component_manager.standby()
        assert result_code == ResultCode.OK

    def test_InvalidSysParam(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test if component manager handles invalid sys param
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        with open(json_file_path + "sys_param_dup_vcc.json") as f:
            sp = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(sp)
        assert result_code == ResultCode.FAILED

        with open(json_file_path + "sys_param_invalid_rec_id.json") as f:
            sp = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(sp)
        assert result_code == ResultCode.FAILED

        with open(json_file_path + "sys_param_dup_dishid.json") as f:
            sp = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(sp)
        assert result_code == ResultCode.FAILED

    def test_sys_param_valid_source_and_filepath(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test if the component manager handles retrieving the sys param file with a valid source and filepath
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        with open(json_file_path + "source_init_sys_param.json") as f:
            sys_param = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(
            sys_param
        )
        assert result_code == ResultCode.OK
        self.assert_sysparam_attributes_match_expected_outcome(
            controller_component_manager, sys_param
        )

    def test_sys_param_valid_source_and_filepath_then_file_only(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test if the component manager properly handles the scenario where it initially
        retrieves the sys param file with a valid source and filepath,
        followed by sending the sys param file directly
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        with open(json_file_path + "source_init_sys_param.json") as f:
            sys_param = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(
            sys_param
        )
        assert result_code == ResultCode.OK
        self.assert_sysparam_attributes_match_expected_outcome(
            controller_component_manager, sys_param
        )

        with open(json_file_path + "sys_param_4_boards.json") as f:
            sys_param_no_retrieve = f.read()

        (result_code, _) = controller_component_manager.init_sys_param(
            sys_param_no_retrieve
        )
        assert result_code == ResultCode.OK
        assert controller_component_manager._source_init_sys_param == ""
        assert (
            controller_component_manager._last_init_sys_param
            == sys_param_no_retrieve
        )

    def test_sys_param_invalid_source(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test if the component manager handles retrieving the sys param file with an invalid source
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        with open(
            json_file_path + "source_init_sys_param_invalid_source.json"
        ) as f:
            sys_param_invalid_source = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(
            sys_param_invalid_source
        )
        assert result_code == ResultCode.FAILED
        assert controller_component_manager._source_init_sys_param == ""
        assert controller_component_manager._last_init_sys_param == ""

    def test_sys_param_valid_source_and_filepath_then_invalid_source(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test if the component manager properly handles the scenario where it initially
        retrieves the sys param file with a valid source and filepath,
        followed by sending another command with an invalid source
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        with open(json_file_path + "source_init_sys_param.json") as f:
            sys_param = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(
            sys_param
        )
        assert result_code == ResultCode.OK
        self.assert_sysparam_attributes_match_expected_outcome(
            controller_component_manager, sys_param
        )

        with open(
            json_file_path + "source_init_sys_param_invalid_source.json"
        ) as f:
            sys_param_unusable_source = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(
            sys_param_unusable_source
        )
        assert result_code == ResultCode.FAILED
        self.assert_sysparam_attributes_match_expected_outcome(
            controller_component_manager, sys_param
        )

    def test_sys_param_invalid_filepath(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test if the component manager handles retrieving the sys param file with an invalid filepath
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True

        with open(
            json_file_path + "source_init_sys_param_invalid_file.json"
        ) as f:
            sys_param_invalid_file = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(
            sys_param_invalid_file
        )
        assert result_code == ResultCode.FAILED
        assert controller_component_manager._source_init_sys_param == ""
        assert controller_component_manager._last_init_sys_param == ""

    def test_sys_param_send_invalid_schema(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
    ) -> None:
        """
        Test if the component manager handles the scenario where it has a schema error
        """
        controller_component_manager.start_communicating()
        assert (
            controller_component_manager.communication_status
            == CommunicationStatus.ESTABLISHED
        )
        assert controller_component_manager._connected is True
        with open(
            json_file_path + "source_init_sys_param_invalid_schema.json"
        ) as f:
            sp = f.read()
        (result_code, _) = controller_component_manager.init_sys_param(sp)
        assert result_code == ResultCode.FAILED
        assert controller_component_manager._source_init_sys_param == ""
        assert controller_component_manager._last_init_sys_param == ""

    def assert_sysparam_attributes_match_expected_outcome(
        self: TestControllerComponentManager,
        controller_component_manager: ControllerComponentManager,
        source_init_sys_param: str,
    ):
        assert (
            controller_component_manager._source_init_sys_param
            == source_init_sys_param
        )
        with open(json_file_path + "sys_param_4_boards.json") as f:
            retrieved_sys_param_file_contents = f.read().replace("\n", "")
        assert controller_component_manager._last_init_sys_param.replace(
            " ", ""
        ) == retrieved_sys_param_file_contents.replace(" ", "")
