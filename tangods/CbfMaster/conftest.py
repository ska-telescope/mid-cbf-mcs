"""
A module defining a list of fixture functions that are shared across all the skabase
tests.
"""

from __future__ import absolute_import
#import mock
import pytest
import importlib
import sys
sys.path.insert(0, "../commons")

from tango import DeviceProxy
from tango.test_context import DeviceTestContext
import global_enum

@pytest.fixture(scope="class")
def create_cbf_master_proxy():
    return DeviceProxy("mid_csp_cbf/sub_elt/master")

@pytest.fixture(scope="class")
def create_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/sub_elt/subarray_01")

@pytest.fixture(scope="class")
def create_subarray_2_proxy():
    return DeviceProxy("mid_csp_cbf/sub_elt/subarray_02")

@pytest.fixture(scope="class")
def create_sw_1_proxy():
    return DeviceProxy("mid_csp_cbf/sw1/01")

@pytest.fixture(scope="class")
def create_sw_2_proxy():
    return DeviceProxy("mid_csp_cbf/sw2/01")

@pytest.fixture(scope="class")
def create_vcc_proxies():
    return [DeviceProxy("mid_csp_cbf/vcc/" + str(i + 1).zfill(3)) for i in range(4)]

@pytest.fixture(scope="class")
def create_fsp_1_proxy():
    return DeviceProxy("mid_csp_cbf/fsp/01")

@pytest.fixture(scope="class")
def create_fsp_2_proxy():
    return DeviceProxy("mid_csp_cbf/fsp/02")

@pytest.fixture(scope="class")
def create_fsp_3_proxy():
    return DeviceProxy("mid_csp_cbf/fsp/03")

@pytest.fixture(scope="class")
def create_fsp_1_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspCorrSubarray/01_01")

@pytest.fixture(scope="class")
def create_fsp_2_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspCorrSubarray/02_01")
