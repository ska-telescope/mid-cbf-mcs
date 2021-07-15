"""
A module defining a list of fixture functions that are shared across all the skabase
tests.
"""

from __future__ import absolute_import
#import mock
import pytest
import logging
import importlib
import os
import sys
import time
import json

# sys.path.insert(0, "tangods/commons")

# file_path = os.path.dirname(os.path.abspath(__file__))
# commons_pkg_path = os.path.abspath(os.path.join(file_path, "tangods/commons"))
# sys.path.insert(0, commons_pkg_path)

# import global_enum

import tango
from tango import DevState
from tango import DeviceProxy
from tango.test_context import MultiDeviceTestContext

from ska_tango_base.control_model import LoggingLevel, ObsState, AdminMode

#TODO clean up file path navigation with proper packaging

path = os.path.join(os.path.dirname(__file__), "tangods/")
sys.path.insert(0, os.path.abspath(path))

from DeviceFactory.DeviceFactory import DeviceFactory

def pytest_addoption(parser):
    """
    Pytest hook; implemented to add the `--true-context` option, used to
    indicate that a true Tango subsystem is available, so there is no
    need for a :py:class:`tango.test_context.MultiDeviceTestContext`.

    :param parser: the command line options parser
    :type parser: :py:class:`argparse.ArgumentParser`
    """
    parser.addoption(
        "--true-context",
        action="store_true",
        default=False,
        help=(
            "Tell pytest that you have a true Tango context and don't "
            "need to spin up a Tango test context"
        ),
    )

@pytest.fixture
def tango_context(devices_to_load, request):
    true_context = request.config.getoption("--true-context")
    logging.info("true context: %s", true_context)
    if not true_context:
        with MultiDeviceTestContext(devices_to_load, process=False) as context:
            DeviceFactory._test_context = context
            yield context
    else:
        yield None

@pytest.fixture(name="proxies", scope="session")
def init_proxies_fixture():

    class Proxies:
        def __init__(self):
            # NOTE: set debug_device_is_on to True in order
            #       to allow device debugging under VScode
            self.debug_device_is_on = False
            if self.debug_device_is_on:
                # Increase the timeout in order to allow  time for debugging
                timeout_millis = 500000
            else:
                timeout_millis = 60000

            self.vcc = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/vcc/" + str(j + 1).zfill(3)) for j in range(4)]):
                proxy.loggingLevel = LoggingLevel.DEBUG
                self.vcc[i + 1] = proxy

            band_tags = ["12", "3", "4", "5"]
            self.vccBand = [[DeviceProxy("mid_csp_cbf/vcc_band{0}/{1:03d}".format(j, k + 1)) for j in band_tags] for k in range(4)]
            self.vccTdc = [[DeviceProxy("mid_csp_cbf/vcc_sw{0}/{1:03d}".format(j, i + 1)) for j in ["1", "2"]] for i in range(4)] 
            
            self.fspSubarray = {} # index 1, 2 = corr (01_01, 02_01); index 3, 4 = pss (03_01, 04_01); index 5, 6 = pst (01_01, 02_01)
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/fspCorrSubarray/" + str(j + 1).zfill(2) + "_01") for j in range(2)]):
                proxy.loggingLevel = LoggingLevel.DEBUG
                self.fspSubarray[i + 1] = proxy
            for i ,proxy in enumerate([DeviceProxy("mid_csp_cbf/fspPssSubarray/" + str(j + 3).zfill(2) + "_01") for j in range(2)]):
                proxy.loggingLevel = LoggingLevel.DEBUG
                self.fspSubarray[i + 3] = proxy
            for i ,proxy in enumerate([DeviceProxy("mid_csp_cbf/fspPstSubarray/" + str(j + 1).zfill(2) + "_01") for j in range(2)]):
                proxy.Init()
                self.fspSubarray[i + 5] = proxy

            self.fsp1FunctionMode = [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/01".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]
            self.fsp2FunctionMode = [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/02".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]
            self.fsp3FunctionMode = [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/03".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]
            self.fsp4FunctionMode = [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/04".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]

            self.fsp = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/fsp/" + str(j + 1).zfill(2)) for j in range(4)]):
                proxy.loggingLevel = LoggingLevel.DEBUG
                proxy.Init()
                self.fsp[i + 1] = proxy

            # self.sw = {}
            # for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/sw" + str(j + 1) + "/01") for j in range(2)]):
            #     proxy.Init()
            #     self.sw[i + 1] = proxy
            
            self.master = DeviceProxy("mid_csp_cbf/sub_elt/master")
            self.master.loggingLevel = LoggingLevel.DEBUG
            self.master.set_timeout_millis(timeout_millis)
            self.master.Init()
            self.wait_timeout_dev([self.master], DevState.STANDBY, 3, 0.05)
            
            self.receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in self.master.receptorToVcc)
            
            self.subarray = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/sub_elt/subarray_" + str(i + 1).zfill(2)) for i in range(3)]):
                proxy.loggingLevel = LoggingLevel.DEBUG
                self.subarray[i + 1] = proxy
                self.subarray[i + 1].set_timeout_millis(timeout_millis)

            self.tm = DeviceProxy("ska_mid/tm_leaf_node/csp_subarray_01")
            self.tm.Init()

        def clean_proxies(self):
            self.receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in self.master.receptorToVcc)
            for proxy in [self.subarray[i + 1] for i in range(1)]:
                if proxy.obsState == ObsState.SCANNING:
                    proxy.EndScan()
                    self.wait_timeout_obs([proxy], ObsState.READY, 3, 0.05)
                if proxy.obsState == ObsState.READY:
                    proxy.GoToIdle()
                    self.wait_timeout_obs([proxy], ObsState.IDLE, 3, 0.05)
                if proxy.obsState == ObsState.IDLE:
                    proxy.RemoveAllReceptors()
                    self.wait_timeout_obs([proxy], ObsState.EMPTY, 3, 0.05)
                if proxy.obsState == ObsState.EMPTY:
                    proxy.Off()
                    self.wait_timeout_dev([proxy], DevState.OFF, 3, 0.05)
                    for vcc_proxy in [self.vcc[i + 1] for i in range(4)]:
                        if vcc_proxy.State() == DevState.ON:
                            vcc_proxy.Off()
                            self.wait_timeout_dev([vcc_proxy], DevState.OFF, 1, 0.05)
                    for fsp_proxy in [self.fsp[i + 1] for i in range(4)]:
                        if fsp_proxy.State() == DevState.ON:
                            fsp_proxy.Off()
                            self.wait_timeout_dev([fsp_proxy], DevState.OFF, 1, 0.05)
        
        def wait_timeout_dev(self, proxygroup, state, time_s, sleep_time_s):
            #time.sleep(time_s)
            timeout = time.time_ns() + (time_s * 1_000_000_000)
            while time.time_ns() < timeout:
                for proxy in proxygroup:
                    if proxy.State() == state: break
                time.sleep(sleep_time_s)

        def wait_timeout_obs(self, proxygroup, state, time_s, sleep_time_s):
            #time.sleep(time_s)
            timeout = time.time_ns() + (time_s * 1_000_000_000)
            while time.time_ns() < timeout:
                for proxy in proxygroup:
                    if proxy.obsState == state: break
                time.sleep(sleep_time_s)
    
    return Proxies()

@pytest.fixture(scope="class")
def debug_device_is_on():
    # NOTE: set debug_device_is_on to True in order
    #       to allow device debugging under VScode
    debug_device_is_on = False
    if debug_device_is_on:
        # Increase the timeout in order to allow  time for debugging
        timeout_millis = 500000
    return debug_device_is_on

@pytest.fixture(scope="class")
def create_vcc_proxy():
    dp = DeviceProxy("mid_csp_cbf/vcc/001")
    dp.loggingLevel = LoggingLevel.DEBUG
    return dp

@pytest.fixture(scope="class")
def create_band_12_proxy():
    #return DeviceTestContext(VccBand1And2)
    return DeviceProxy("mid_csp_cbf/vcc_band12/001")

@pytest.fixture(scope="class")
def create_band_3_proxy():
    #return DeviceTestContext(VccBand3)
    return DeviceProxy("mid_csp_cbf/vcc_band3/001")

@pytest.fixture(scope="class")
def create_band_4_proxy():
    #return DeviceTestContext(VccBand4)
    return DeviceProxy("mid_csp_cbf/vcc_band4/001")

@pytest.fixture(scope="class")
def create_band_5_proxy():
    #return DeviceTestContext(VccBand5)
    return DeviceProxy("mid_csp_cbf/vcc_band5/001")

@pytest.fixture(scope="class")
def create_sw_1_proxy():
    #return DeviceTestContext(VccSearchWindow)
    return DeviceProxy("mid_csp_cbf/vcc_sw1/001")

@pytest.fixture(scope="class")
def create_fsp_corr_subarray_1_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspCorrSubarray/01_01")

@pytest.fixture(scope="class")
def create_fsp_pss_subarray_2_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspPssSubarray/02_01")

@pytest.fixture(scope="class")
def create_corr_proxy():
    return DeviceProxy("mid_csp_cbf/fsp_corr/01")

@pytest.fixture(scope="class")
def create_pss_proxy():
    return DeviceProxy("mid_csp_cbf/fsp_pss/01")

def load_data(name):
    """
    Loads a dataset by name. This implementation uses the name to find a
    JSON file containing the data to be loaded.

    :param name: name of the dataset to be loaded; this implementation
        uses the name to find a JSON file containing the data to be
        loaded.
    :type name: string
    """
    with open(f"tests/data/{name}.json", "r") as json_file:
        return json.load(json_file)
