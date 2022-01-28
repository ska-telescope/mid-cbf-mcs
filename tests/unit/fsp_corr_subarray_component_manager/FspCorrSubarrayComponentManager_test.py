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

from ska_mid_cbf_mcs.fsp.fsp_corr_subarray_component_manager import FspCorrSubarrayComponentManager 
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.testing.mock.mock_callable import MockCallable

import pytest

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

   