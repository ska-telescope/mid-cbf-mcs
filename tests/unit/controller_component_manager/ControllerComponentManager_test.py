#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the Talon-DX component manager."""
import tango
from tango import DevState
import time
import pytest
from ska_mid_cbf_mcs.controller.controller_component_manager import ControllerComponentManager

def test_On(
    controller_component_manager: ControllerComponentManager,
) -> None:
    """
    Test On command.

    :param device_under_test: fixture that provides a
        :py:class:`CbfDeviceProxy` to the device under test, in a
        :py:class:`tango.test_context.DeviceTestContext`.
    """
    time.sleep(1)



