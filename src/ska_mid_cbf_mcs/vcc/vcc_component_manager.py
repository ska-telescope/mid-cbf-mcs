# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

"""
VccComponentManager
Sub-element VCC component manager for Mid.CBF
"""
from __future__ import annotations  # allow forward references in type hints

from typing import List, Tuple

import logging
import json

# tango imports
import tango
from tango.server import BaseDevice, Device, run
from tango.server import attribute, command
from tango.server import device_property
from tango import DevFailed, DebugIt, DevState, AttrWriteType

# SKA Specific imports

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

from ska_tango_base.control_model import ObsState
from ska_tango_base import SKAObsDevice, CspSubElementObsDevice
from ska_tango_base.commands import ResultCode

class VccComponentManager:
    """Component manager for Vcc class."""

    def __init__(
        self: VccComponentManager,
        vcc_id: int,
        vcc_band: List[str],
        search_window: List[str],
        logger: logging.Logger,
        connect: bool = True
    ) -> None:
        """
        Initialize a new instance.

        :param vcc_id: ID of VCC
        :param vcc_band: FQDNs of VCC band devices
        :param search_window: FQDNs of VCC search windows
        :param logger: a logger for this object to use
        :param connect: whether to connect automatically upon initialization
        """
        self._vcc_id = vcc_id
        self._vcc_band_fqdn = vcc_band
        self._search_window_fqdn = search_window

        self._logger = logger

        self._connected = False

        # initialize attribute values
        self._receptor_ID = 0
        self._freq_band_name = ""
        self._frequency_band = 0
        self._subarray_membership = 0
        self._stream_tuning = (0, 0)
        self._frequency_band_offset_stream_1 = 0
        self._frequency_band_offset_stream_2 = 0
        self._doppler_phase_correction = (0, 
        0, 0, 0)
        self._rfi_flagging_mask = ""
        self._scfo_band_1 = 0
        self._scfo_band_2 = 0
        self._scfo_band_3 = 0
        self._scfo_band_4 = 0
        self._scfo_band_5a = 0
        self._scfo_band_5b = 0
        self._delay_model = [[0] * 6 for i in range(26)]
        self._jones_matrix = [[0] * 16 for i in range(26)]

        self._scan_id = ""
        self._config_id = ""

        self._proxy_band_12 = None
        self._proxy_band_3 = None
        self._proxy_band_4 = None
        self._proxy_band_5 = None

        if connect:
            self.start_communicating()


    def start_communicating(self: VccComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""

        if self._connected:
            self._logger.info("Already connected.")
            return
        
        try:
            self._proxy_band_12 = CbfDeviceProxy(
                fqdn=self._vcc_band_fqdn[0],
                logger=self._logger
            )
            self._proxy_band_3 = CbfDeviceProxy(
                fqdn=self._vcc_band_fqdn[1],
                logger=self._logger
            )
            self._proxy_band_4 = CbfDeviceProxy(
                fqdn=self._vcc_band_fqdn[2],
                logger=self._logger
            )
            self._proxy_band_5 = CbfDeviceProxy(
                fqdn=self._vcc_band_fqdn[3],
                logger=self._logger
            )
            self._proxy_sw_1 = CbfDeviceProxy(
                fqdn=self._search_window_fqdn[0],
                logger=self._logger
            )
            self._proxy_sw_2 = CbfDeviceProxy(
                fqdn=self._search_window_fqdn[1],
                logger=self._logger
            )
        except tango.DevFailed as dev_failed:
            raise ConnectionError(
                f"Error in proxy connection."
            ) from dev_failed
        
        self._connected = True


    def stop_communicating(self: VccComponentManager) -> None:
        """Stop communication with the component."""
        self._connected = False


    def turn_on_band_device(
        self: VccComponentManager,
        freq_band_name: str
    ) -> None:
        """
        Turn on the corresponding band device and disable all the others.

        :param freq_band_name: the frequency band name
        """

        # TODO: can be done in a more Pythonian way; broken?
        if freq_band_name in ["1", "2"]:
            self._proxy_band_12.On()
            self._proxy_band_3.Disable()
            self._proxy_band_4.Disable()
            self._proxy_band_5.Disable()
        elif freq_band_name == "3":
            self._proxy_band_12.Disable()
            self._proxy_band_3.On()
            self._proxy_band_4.Disable()
            self._proxy_band_5.Disable()
        elif freq_band_name == "4":
            self._proxy_band_12.Disable()
            self._proxy_band_3.Disable()
            self._proxy_band_4.On()
            self._proxy_band_5.Disable()
        elif freq_band_name in ["5a", "5b"]:
            self._proxy_band_12.Disable()
            self._proxy_band_3.Disable()
            self._proxy_band_4.Disable()
            self._proxy_band_5.On()
        else:
            # The frequency band name has been validated at this point
            # so this shouldn't happen
            pass


    def turn_off_band_device(
        self:VccComponentManager,
        freq_band_name: str
    ) -> None:
        """
        Send OFF signal to the corresponding band

        :param freq_band_name: the frequency band name
        """
        # TODO: can be done in a more Pythonian way; broken?
        if freq_band_name in ["1", "2"]:
            self._proxy_band_12.Off()
        elif freq_band_name == "3":
            self._proxy_band_3.Off()
        elif freq_band_name == "4":
            self._proxy_band_4.Off()
        elif freq_band_name in ["5a", "5b"]:
            self._proxy_band_5.Off()
        else:
            # The frequency band name has been validated at this point
            # so this shouldn't happen
            pass


    def _raise_configure_scan_fatal_error(
        self: VccComponentManager, 
        msg: str
        ) -> None:
        """
        Raise fatal error in ConfigureScan execution

        :param msg: error message
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._logger.error(msg)
        tango.Except.throw_exception(
            "Command failed", msg, "ConfigureScan execution", tango.ErrSeverity.ERR
        )
        return (ResultCode.FAILED, msg)


    def _validate_scan_configuration(
        self: VccComponentManager, 
        argin: str
        ) -> Tuple[bool, str]:
        """
        Validate the configuration parameters against allowed values, as needed.

        :param argin: The JSON formatted string with configuration for the device.
            :type argin: 'DevString'
        :return: A tuple containing a boolean indicating if the configuration
        is valid and a string message. The message is for information 
        purpose only.
        :rtype: (bool, str)

        """
        try:
            configuration = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Scan configuration object is not a valid JSON object. Aborting configuration."
            return (False, msg)

        # Validate configID.
        if "config_id" not in configuration:
            msg = "'configID' attribute is required."
            return (False, msg)
        
        # Validate frequencyBand.
        if "frequency_band" not in configuration:
            msg = "'frequencyBand' attribute is required."
            return (False, msg)
        
        # Validate frequencyBandOffsetStream1.
        if "frequency_band_offset_stream_1" not in configuration:
            configuration["frequency_band_offset_stream_1"] = 0
        if abs(int(configuration["frequency_band_offset_stream_1"])) <= const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
            pass
        else:
            msg = "Absolute value of 'frequencyBandOffsetStream1' must be at most half " \
                    "of the frequency slice bandwidth. Aborting configuration."
            return (False, msg)

        # Validate frequencyBandOffsetStream2.
        if "frequency_band_offset_stream_2" not in configuration:
            configuration["frequency_band_offset_stream_2"] = 0
        if abs(int(configuration["frequency_band_offset_stream_2"])) <= const.FREQUENCY_SLICE_BW * 10 ** 6 / 2:
            pass
        else:
            msg = "Absolute value of 'frequencyBandOffsetStream2' must be at most " \
                    "half of the frequency slice bandwidth. Aborting configuration."
            return (False, msg)
        
        # Validate frequencyBand.
        valid_freq_bands = ["1", "2", "3", "4", "5a", "5b"]
        if configuration["frequency_band"] not in valid_freq_bands:
            msg = "'band5Tuning' must be an array of length 2. Aborting configuration."
            return (False, msg)

        # Validate band5Tuning, frequencyBandOffsetStream2 if frequencyBand is 5a or 5b.
        if configuration["frequency_band"] in ["5a", "5b"]:
            # band5Tuning is optional
            if "band_5_tuning" in configuration:
                pass
                # check if streamTuning is an array of length 2
                try:
                    assert len(configuration["band_5_tuning"]) == 2
                except (TypeError, AssertionError):
                    msg = "'band5Tuning' must be an array of length 2. Aborting configuration."
                    return (False, msg)

                stream_tuning = [*map(float, configuration["band_5_tuning"])]
                if configuration["frequency_band"] == "5a":
                    if all(
                            [const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0] <= stream_tuning[i]
                            <= const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1] for i in [0, 1]]
                    ):
                        pass
                    else:
                        msg = "Elements in 'band5Tuning must be floats between {} and {} " \
                            "(received {} and {}) for a 'frequencyBand' of 5a. " \
                            "Aborting configuration.".format(
                            const.FREQUENCY_BAND_5a_TUNING_BOUNDS[0],
                            const.FREQUENCY_BAND_5a_TUNING_BOUNDS[1],
                            stream_tuning[0],
                            stream_tuning[1]
                        )
                        self._raise_configure_scan_fatal_error(msg)
                else:  # configuration["frequency_band"] == "5b"
                    if all(
                            [const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0] <= stream_tuning[i]
                            <= const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1] for i in [0, 1]]
                    ):
                        pass
                    else:
                        msg = "Elements in 'band5Tuning must be floats between {} and {} " \
                            "(received {} and {}) for a 'frequencyBand' of 5b. " \
                            "Aborting configuration.".format(
                            const.FREQUENCY_BAND_5b_TUNING_BOUNDS[0],
                            const.FREQUENCY_BAND_5b_TUNING_BOUNDS[1],
                            stream_tuning[0],
                            stream_tuning[1]
                        )
                        return (False, msg)
            else:
                # set band5Tuning to zero for the rest of the test. This won't 
                # change the argin in function "configureScan(argin)"
                configuration["band_5_tuning"] = [0, 0]
        
        return (True, "ConfigureScan command completed OK.")


    def configure_scan(
        self: VccComponentManager,
        argin: str
    ) -> Tuple[ResultCode, str]:
        """
        Configure scan parameters.

        :param argin: The configuration as JSON formatted string
        :type argin: str

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        :raises: ``CommandError`` if the configuration data validation fails.
        """

        # By this time, the receptor_ID should be set:
        self._logger.debug(("self._receptor_ID = {}".
        format(self._receptor_ID)))

        # This validation is already performed in the CbfSubbarray ConfigureScan.
        # TODO: Improve validation (validation should only be done once,
        # most of the validation can be done through a schema instead of manually
        # through functions).
        (valid, msg) = self._validate_scan_configuration(argin)
        if not valid:
            return self._raise_configure_scan_fatal_error(msg)
        
        configuration = json.loads(argin)

        self._config_id = configuration["config_id"]

        # TODO: The frequency band attribute is optional but 
        # if not specified the previous frequency band set should be used 
        # (see Mid.CBF Scan Configuration in ICD). Therefore, the previous frequency 
        # band value needs to be stored, and if the frequency band is not
        # set in the config it should be replaced with the previous value.
        self._frequency_band = int(configuration["frequency_band"])
        frequency_bands = ["1", "2", "3", "4", "5a", "5b"]
        self._freq_band_name =  frequency_bands[self._frequency_band]
        if self._frequency_band in [4, 5]:
                self._stream_tuning = configuration["band_5_tuning"]

        self._frequency_band_offset_stream_1 = int(configuration["frequency_band_offset_stream_1"])
        self._frequency_band_offset_stream_2 = int(configuration["frequency_band_offset_stream_2"])
        
        if "rfi_flagging_mask" in configuration:
            self._rfi_flagging_mask = str(configuration["rfi_flagging_mask"])
        else:
            self._logger.warn("'rfiFlaggingMask' not given. Proceeding.")

        if "scfo_band_1" in configuration:
            self._scfo_band_1 = int(configuration["scfo_band_1"])
        else:
            self._scfo_band_1 = 0
            self._logger.warn("'scfoBand1' not specified. Defaulting to 0.")

        if "scfo_band_2" in configuration:
            self._scfo_band_2 = int(configuration["scfo_band_2"])
        else:
            self._scfo_band_2 = 0
            self._logger.warn("'scfoBand2' not specified. Defaulting to 0.")

        if "scfo_band_3" in configuration:
            self._scfo_band_3 = int(configuration["scfo_band_3"])
        else:
            self._scfo_band_3 = 0
            self._logger.warn("'scfoBand3' not specified. Defaulting to 0.")

        if "scfo_band_4" in configuration:
            self._scfo_band_4 = configuration["scfo_band_4"]
        else:
            self._scfo_band_4 = 0
            self._logger.warn("'scfoBand4' not specified. Defaulting to 0.")

        if "scfo_band_5a" in configuration:
            self._scfo_band_5a = int(configuration["scfo_band_5a"])
        else:
            self._scfo_band_5a = 0
            self._logger.warn("'scfoBand5a' not specified. Defaulting to 0.")

        if "scfo_band_5b" in configuration:
            self._scfo_band_5b = int(configuration["scfo_band_5b"])
        else:
            self._scfo_band_5b = 0
            self._logger.warn("'scfoBand5b' not specified. Defaulting to 0.")

        # store the configuration on command success
        self._last_scan_configuration = argin

        return(ResultCode.OK, msg)


