# -*- coding: utf-8 -*-
#
# This file is part of the TmCspSubarrayLeafNodeTest project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

""" TmCspSubarrayLeafNodeTest Tango device prototype

TmCspSubarrayLeafNodeTest TANGO device class for the CBF prototype
"""

# PyTango imports
import PyTango
from PyTango import DebugIt
from PyTango.server import run
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command
from PyTango.server import device_property
from PyTango import AttrQuality, DispLevel, DevState
from PyTango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.additionnal_import) ENABLED START #
import os
import sys
import json
from random import randint

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../commons"))
sys.path.insert(0, commons_pkg_path)

from skabase.SKABaseDevice.SKABaseDevice import SKABaseDevice
from global_enum import HealthState, AdminMode
# PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.additionnal_import

__all__ = ["TmCspSubarrayLeafNodeTest", "main"]


class TmCspSubarrayLeafNodeTest(SKABaseDevice):
    """
    TmCspSubarrayLeafNodeTest TANGO device class for the CBF prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.class_variable) ENABLED START #

    def __output_links_event_callback(self, event):
        if not event.err:
            try:
                log_msg = "Received output links."
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)

                output_links = json.loads(str(event.attr_value.value))
                scan_ID = int(output_links["scanID"])

                if not scan_ID or self._received_output_links:
                    log_msg = "Skipped assigning destination addresses."
                    self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
                    return

                self._scan_ID = scan_ID
                self.__generate_visibilities_destination_addresses(output_links)
            except Exception as e:
                self.dev_logging(str(e), PyTango.LogLevel.LOG_ERROR)
        else:
            for item in event.errors:
                log_msg = item.reason + ": on attribute " + str(event.attr_name)
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)

    def __generate_visibilities_destination_addresses(self, output_links):
        destination_addresses = {
            "scanId": output_links["scanID"],
            "receiveAddresses": []
        }

        for fsp_in in output_links["fsp"]:
            fsp = {
                "phaseBinId": 0,
                "fspId": fsp_in["fspID"],
                "hosts": []
            }
            # get the total number of channels and first channel
            num_channels = 0
            first_channel = sys.maxsize
            for link in fsp_in["cbfOutLink"]:
                for channel_in in link["channel"]:
                    num_channels += 1
                    first_channel = min(first_channel, channel_in["chanID"])

            if num_channels:
                fsp["hosts"].append({
                    "host": "192.168.0.1",
                    "channels": [{
                        "portOffset": 8080,
                        "numChannels": num_channels,
                        "startChannel": first_channel
                    }]
                })

            destination_addresses["receiveAddresses"].append(fsp)

        log_msg = "Done assigning destination addresses."
        self.dev_logging(log_msg, PyTango.LogLevel.LOG_WARN)
        # publish the destination addresses
        self._vis_destination_address = destination_addresses
        self.push_change_event("visDestinationAddress", json.dumps(self._vis_destination_address))
        self._received_output_links = True

    # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.class_variable

    # -----------------
    # Device Properties
    # -----------------

    CspMasterAddress = device_property(
        dtype='str'
    )

    CspSubarrayAddress = device_property(
        dtype='str'
    )


    # ----------
    # Attributes
    # ----------

    scanID = attribute(
        dtype='uint',
        access=AttrWriteType.READ,
        label="Scan ID",
        doc="Scan ID",
    )

    dopplerPhaseCorrection = attribute(
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction",
        doc="Doppler phase correction coefficients",
    )

    delayModel = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Delay model coefficients",
        doc="Delay model coefficients"
    )

    visDestinationAddress = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Destination addresses for visibilities",
        doc="Destination addresses for visibilities"
    )

    receivedOutputLinks = attribute(
        dtype='bool',
        access=AttrWriteType.READ,
        label="Received output links",
        doc="Received output links"
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKABaseDevice.init_device(self)
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.init_device) ENABLED START #
        self.set_state(DevState.INIT)

        self._storage_logging_level = PyTango.LogLevel.LOG_DEBUG
        self._element_logging_level = PyTango.LogLevel.LOG_DEBUG
        self._central_logging_level = PyTango.LogLevel.LOG_DEBUG

        self._scan_ID = 0
        self._doppler_phase_correction = [0, 0, 0, 0]
        self._delay_model = {}  # this is interpreted as a JSON object
        self._vis_destination_address = {}  # this is interpreted as a JSON object
        self._received_output_links = False

        self._proxy_csp_master = PyTango.DeviceProxy(self.CspMasterAddress)
        self._proxy_cbf_master = PyTango.DeviceProxy(
            self._proxy_csp_master.get_property("CspMidCbf")["CspMidCbf"][0]
        )
        self._proxy_csp_subarray = PyTango.DeviceProxy(self.CspSubarrayAddress)

        self._proxy_csp_subarray.subscribe_event(
            "cbfOutputLink",
            PyTango.EventType.CHANGE_EVENT,
            self.__output_links_event_callback,
            stateless=True
        )

        self.set_state(DevState.STANDBY)
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_scanID(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.scanID_read) ENABLED START #
        return self._scan_ID
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.scanID_read

    def read_dopplerPhaseCorrection(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.dopplerPhaseCorrection_read) ENABLED START #
        return self._doppler_phase_correction
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.dopplerPhaseCorrection_read

    def write_dopplerPhaseCorrection(self, value):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.dopplerPhaseCorrection_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.dopplerPhaseCorrection_write

    def read_delayModel(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.delayModel_read) ENABLED START #
        return json.dumps(self._delay_model)
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.delayModel_read

    def write_delayModel(self, value):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.delayModel_write) ENABLED START #
        # since this is just a test device, assume that the JSON schema is always what we expect
        self._delay_model = json.loads(str(value))
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.delayModel_write

    def read_visDestinationAddress(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.visDestinationAddress_read) ENABLED START #
        return json.dumps(self._vis_destination_address)
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.visDestinationAddress_read

    def write_visDestinationAddress(self, value):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.visDestinationAddress_write) ENABLED START #
        # since this is just a test device, assume that the JSON schema is always what we expect
        self._vis_destination_address = json.loads(str(value))
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.visDestinationAddress_write

    def read_receivedOutputLinks(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.receivedOutputLinks_read) ENABLED START #
        return self._received_output_links
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.receivedOutputLinks_read

    # --------
    # Commands
    # --------


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.main) ENABLED START #
    return run((TmCspSubarrayLeafNodeTest,), args=args, **kwargs)
    # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.main

if __name__ == '__main__':
    main()
