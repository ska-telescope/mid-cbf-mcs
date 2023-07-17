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
# Additional import
# PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.additionnal_import) ENABLED START #
# tango imports

import json  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402

import tango  # noqa: E402
from ska_tango_base import SKABaseDevice  # noqa: E402
from tango import AttrWriteType, DevState  # noqa: E402
from tango.server import attribute, device_property, run  # noqa: E402

file_path = os.path.dirname(os.path.abspath(__file__))

# PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.additionnal_import

__all__ = ["TmCspSubarrayLeafNodeTest", "main"]


class TmCspSubarrayLeafNodeTest(SKABaseDevice):
    """
    TmCspSubarrayLeafNodeTest TANGO device class for the CBF prototype
    """

    # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.class_variable) ENABLED START #

    def __output_links_event_callback(self, event):
        self.logger.info(
            f"__output_links_event_callback: {self._received_output_links}"
        )
        if not event.err:
            try:
                log_msg = "Received output links."
                self.logger.warning(log_msg)

                output_links = json.loads(str(event.attr_value.value))
                config_ID = output_links["configID"]

                if not config_ID or self._received_output_links:
                    log_msg = "Skipped assigning destination addresses."
                    self.logger.warning(log_msg)
                    return

                self._config_ID = config_ID
                self.__generate_visibilities_destination_addresses(
                    output_links
                )
            except Exception as e:
                self.logger.error(str(e))
        else:
            for item in event.errors:
                log_msg = f"{item.reason}: on attribute {event.attr_name}"
                self.logger.error(log_msg)

    def __generate_visibilities_destination_addresses(self, output_links):
        destination_addresses = {
            "configID": output_links["configID"],
            "receiveAddresses": [],
        }

        for fsp_in in output_links["fsp"]:
            fsp = {"phaseBinId": 0, "fspId": fsp_in["fspID"], "hosts": []}
            # get the total number of channels and first channel
            num_channels = 0
            first_channel = sys.maxsize
            for link in fsp_in["cbfOutLink"]:
                for channel_in in link["channel"]:
                    num_channels += 1
                    first_channel = min(first_channel, channel_in["chanID"])

            if num_channels:
                fsp["hosts"].append(
                    {
                        "host": "192.168.0.1",
                        "channels": [
                            {
                                "portOffset": 8080,
                                "numChannels": num_channels,
                                "startChannel": first_channel,
                            }
                        ],
                    }
                )

            destination_addresses["receiveAddresses"].append(fsp)

        log_msg = "Done assigning destination addresses."
        self.logger.warning(log_msg)
        # publish the destination addresses
        self._vis_destination_address = destination_addresses
        self.push_change_event(
            "visDestinationAddress", json.dumps(self._vis_destination_address)
        )
        self._received_output_links = True

    # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.class_variable

    # -----------------
    # Device Properties
    # -----------------

    CbfControllerAddress = device_property(dtype="str")

    CbfSubarrayAddress = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    configID = attribute(
        dtype="str",
        access=AttrWriteType.READ,
        label="Config ID",
        doc="Config ID. Takes in 'id' in the input JSON file",
    )

    dopplerPhaseCorrection = attribute(
        dtype="float",
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction",
        doc="Doppler phase correction coefficients",
    )

    jonesMatrix = attribute(
        dtype="str",
        access=AttrWriteType.READ_WRITE,
        label="Jones matrix",
        doc="Jones matrix",
    )

    delayModel = attribute(
        dtype="str",
        access=AttrWriteType.READ_WRITE,
        label="Delay model coefficients",
        doc="Delay model coefficients",
    )

    timingBeamWeights = attribute(
        dtype="str",
        access=AttrWriteType.READ_WRITE,
        label="Timing beam weights",
        doc="Timing beam weights",
    )

    visDestinationAddress = attribute(
        dtype="str",
        access=AttrWriteType.READ_WRITE,
        label="Destination addresses for visibilities",
        doc="Destination addresses for visibilities",
    )

    receivedOutputLinks = attribute(
        dtype="bool",
        access=AttrWriteType.READ,
        label="Received output links",
        doc="Received output links",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        SKABaseDevice.init_device(self)
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.init_device) ENABLED START #
        self.set_state(DevState.INIT)

        self._config_ID = ""
        self._doppler_phase_correction = [0.0, 0.0, 0.0, 0.0]
        self._jones_matrix = {}  # this is interpreted as a JSON object
        self._delay_model = {}  # this is interpreted as a JSON object
        self._timing_beam_weights = {}  # this is interpreted as a JSON object
        self._vis_destination_address = (
            {}
        )  # this is interpreted as a JSON object
        self._received_output_links = False

        # decoupling mif-cbf-mcs from csp-mid-lmc so that it can be tested  standalone
        # TmCspSubarrayLeafNodeTest device subscribes directly to the CbfSubarray
        # outputLinksDistribution attribute to received the outputlinks.
        self._proxy_cbf_subarray = tango.DeviceProxy(self.CbfSubarrayAddress)
        # self._proxy_cbf_subarray.subscribe_event(
        #     "outputLinksDistribution",
        #     tango.EventType.CHANGE_EVENT,
        #     self.__output_links_event_callback,
        #     stateless=True,
        # )

        self.set_change_event("delayModel", True, True)

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

    def read_configID(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.configID_read) ENABLED START #
        return self._config_ID
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.configID_read

    def read_dopplerPhaseCorrection(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.dopplerPhaseCorrection_read) ENABLED START #
        return self._doppler_phase_correction
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.dopplerPhaseCorrection_read

    def write_dopplerPhaseCorrection(self, value):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.dopplerPhaseCorrection_write) ENABLED START #
        self.logger.info(
            f"write_dopplerPhaseCorrection: type(value) {type(value)}"
        )
        try:
            if len(value) == 4:
                self._doppler_phase_correction = value
            else:
                log_msg = (
                    "Writing to dopplerPhaseCorrection attribute expected 4 elements, "
                    + f"but received {len(value)}. Ignoring."
                )
                self.logger.error(log_msg)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection attribute must be an array of length 4. Ignoring."
            self.logger.error(log_msg)
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.dopplerPhaseCorrection_write

    def read_jonesMatrix(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.jonesMatrix_read) ENABLED START #
        return json.dumps(self._jones_matrix)
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.jonesMatrix_read

    def write_jonesMatrix(self, value):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.jonesMatrix_write) ENABLED START #
        self._jones_matrix = json.loads(str(value))
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.jonesMatrix_write

    def read_delayModel(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.delayModel_read) ENABLED START #
        return json.dumps(self._delay_model)
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.delayModel_read

    def write_delayModel(self, value):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.delayModel_write) ENABLED START #
        # since this is just a test device, assume that the JSON schema is always what we expect
        self._delay_model = json.loads(str(value))
        self.push_change_event("delayModel", value)
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.delayModel_write

    def read_timingBeamWeights(self):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.timingBeamWeights_read) ENABLED START #
        return json.dumps(self._timing_beam_weights)
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.timingBeamWeights_read

    def write_timingBeamWeights(self, value):
        # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.timingBeamWeights_write) ENABLED START #
        # since this is just a test device, assume that the JSON schema is always what we expect
        self._timing_beam_weights = json.loads(str(value))
        # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.timingBeamWeights_write

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


if __name__ == "__main__":
    main()
