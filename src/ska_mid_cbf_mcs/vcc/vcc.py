# -*- coding: utf-8 -*-
#
# This file is part of the Vcc project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# """
# Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
# Herzberg Astronomy and Astrophysics, National Research Council of Canada
# Copyright (c) 2019 National Research Council of Canada
# """

# Vcc Tango device prototype
# Vcc TANGO device class for the prototype

# PROTECTED REGION ID(Vcc.additionnal_import) ENABLED START #
import os
import sys
import json

# tango imports
import tango
from tango.server import Device, run
from tango.server import attribute, command
from tango.server import device_property
from tango import DebugIt, DevState, AttrWriteType
from tango.test_context import MultiDeviceTestContext

# SKA Specific imports

from ska_mid_cbf_mcs.commons.global_enum import const, freq_band_dict
from ska_mid_cbf_mcs.dev_factory import DevFactory

from ska_tango_base.control_model import ObsState
from ska_tango_base import SKAObsDevice, CspSubElementObsDevice
from ska_tango_base.commands import ResultCode

# PROTECTED REGION END #    //  Vcc.additionnal_import

__all__ = ["Vcc", "main"]


class Vcc(CspSubElementObsDevice):
    """
    Vcc TANGO device class for the prototype
    """

    #TODO: remove temporary manual flag for unit testing
    #set True to bypass band and search window device proxies
    TEST_CONTEXT = False

    # -----------------
    # Device Properties
    # -----------------

    VccID = device_property(
        dtype='DevUShort'
    )

    Band1And2Address = device_property(
        dtype='str'
    )

    Band3Address = device_property(
        dtype='str'
    )

    Band4Address = device_property(
        dtype='str'
    )

    Band5Address = device_property(
        dtype='str'
    )

    SW1Address = device_property(
        dtype='str'
    )

    SW2Address = device_property(
        dtype='str'
    )

    # ----------
    # Attributes
    # ----------

    receptorID = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="Receptor ID",
        doc="Receptor ID",
    )

    subarrayMembership = attribute(
        dtype='uint16',
        access=AttrWriteType.READ_WRITE,
        label="subarrayMembership",
        doc="Subarray membership",
    )

    frequencyBand = attribute(
        dtype='DevEnum',
        access=AttrWriteType.READ,
        label="Frequency band",
        doc="Frequency band; an int in the range [0, 5]",
        enum_labels=["1", "2", "3", "4", "5a", "5b", ],
    )

    band5Tuning = attribute(
        dtype=('float',),
        max_dim_x=2,
        access=AttrWriteType.READ_WRITE,
        label="Stream tuning (GHz)",
        doc="Stream tuning (GHz)"
    )

    frequencyBandOffsetStream1 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="Frequency band offset (stream 1) (Hz)",
        doc="Frequency band offset (stream 1) (Hz)"
    )

    frequencyBandOffsetStream2 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="Frequency band offset (stream 2) (Hz)",
        doc="Frequency band offset (stream 2) (Hz)"
    )

    dopplerPhaseCorrection = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction coefficients",
        doc="Doppler phase correction coefficients"
    )

    rfiFlaggingMask = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="RFI Flagging Mask",
        doc="RFI Flagging Mask"
    )

    scfoBand1 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 1)",
        doc="Sample clock frequency offset for band 1",
    )

    scfoBand2 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 2)",
        doc="Sample clock frequency offset for band 2",
    )

    scfoBand3 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 3)",
        doc="Sample clock frequency offset for band 3",
    )

    scfoBand4 = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 4)",
        doc="Sample clock frequency offset for band 4",
    )

    scfoBand5a = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 5a)",
        doc="Sample clock frequency offset for band 5a",
    )

    scfoBand5b = attribute(
        dtype='int',
        access=AttrWriteType.READ_WRITE,
        label="SCFO (band 5b)",
        doc="Sample clock frequency offset for band 5b",
    )

    delayModel = attribute(
        dtype=(('double',),),
        max_dim_x=6,
        max_dim_y=26,
        access=AttrWriteType.READ,
        label="Delay model coefficients",
        doc="Delay model coefficients, given per frequency slice"
    )

    jonesMatrix = attribute(
        dtype=(('double',),),
        max_dim_x=16,
        max_dim_y=26,
        access=AttrWriteType.READ,
        label='Jones Matrix elements',
        doc='Jones Matrix elements, given per frequency slice'
    )

    scanID = attribute(
        dtype='DevULong',
        access=AttrWriteType.READ_WRITE,
        label="scanID",
        doc="scan ID",
    )

    configID = attribute(
        dtype='DevString',
        access=AttrWriteType.READ_WRITE,
        label="config ID",
        doc="config ID",
    )

    # ---------------
    # General methods
    # ---------------

    # PROTECTED REGION ID(Vcc.class_variable) ENABLED START #

    def init_command_objects(self):
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.state_model, self.logger)
        self.register_command_object(
            "ConfigureScan", self.ConfigureScanCommand(*device_args)
        )
        self.register_command_object(
            "GoToIdle", self.GoToIdleCommand(*device_args)
        )

    # PROTECTED REGION END #    //  Vcc.class_variable

    class InitCommand(CspSubElementObsDevice.InitCommand):
        """
        A class for the Vcc's init_device() "command".
        """

        def do(self):
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering InitCommand()")

            super().do()

            device = self.target

            # Make a private copy of the device properties:
            self._vcc_id = device.VccID

            # initialize attribute values        

            device._receptor_ID = 0
            device._freq_band_name = ""
            device._frequency_band = 0
            device._subarray_membership = 0
            device._stream_tuning = (0, 0)
            device._frequency_band_offset_stream_1 = 0
            device._frequency_band_offset_stream_2 = 0
            device._doppler_phase_correction = (0, 
            0, 0, 0)
            device._rfi_flagging_mask = ""
            device._scfo_band_1 = 0
            device._scfo_band_2 = 0
            device._scfo_band_3 = 0
            device._scfo_band_4 = 0
            device._scfo_band_5a = 0
            device._scfo_band_5b = 0
            device._delay_model = [[0] * 6 for i in range(26)]
            device._jones_matrix = [[0] * 16 for i in range(26)]

            device._scan_id = ""
            device._config_id = ""

            # device._fqdns = [
            #    device.Band1And2Address,
            #    device.Band3Address,
            #    device.Band4Address,
            #    device.Band5Address,
            #    device.SW1Address,
            #    device.SW2Address 
            # ] # TODO 

            # device._func_devices = [
            #     tango.DeviceProxy(fqdn) for fqdn in device._fqdns
            # ]

            device.set_change_event("subarrayMembership", True, True)

            # TODO - create a command for the proxy connections
            #        similar to InitialSetup() in ska-low-mccs stations.py
            
            #self.__get_capability_proxies()

            # TODO - To support unit testing, use a wrapper class for the  
            # connection instead of directly DeviceProxy (see MccsDeviceProxy)
            device._dev_factory = DevFactory()
            device._proxy_band_12 = None
            device._proxy_band_3  = None
            device._proxy_band_4  = None
            device._proxy_band_5  = None
            device._proxy_sw_1    = None
            device._proxy_sw_2    = None

            message = "Vcc Init command completed OK"
            device.logger.info(message)
            return (ResultCode.OK, message)

    def always_executed_hook(self):
        """Method always executed before any TANGO command is executed."""
        # PROTECTED REGION ID(Vcc.always_executed_hook) ENABLED START #
        self.logger.info("ALWAYS EXECUTED HOOK")
        self.logger.info("%s", self._dev_factory._test_context)
        try:
            #TODO: remove temporary flag to disable Vcc proxies for unit testing
            if Vcc.TEST_CONTEXT is False:
                if self._proxy_band_12 is None:
                    self.logger.info("Connect to band proxy device")
                    self._proxy_band_12 = self._dev_factory.get_device(
                        self.Band1And2Address
                    )
                if self._proxy_band_3 is None:
                    self.logger.info("Connect to band proxy device")
                    self._proxy_band_3 = self._dev_factory.get_device(
                        self.Band3Address
                    )
                if self._proxy_band_4 is None:
                    self.logger.info("Connect to band proxy device")
                    self._proxy_band_4 = self._dev_factory.get_device(
                        self.Band4Address
                    )
                if self._proxy_band_5 is None:
                    self.logger.info("Connect to band proxy device")
                    self._proxy_band_5 = self._dev_factory.get_device(
                        self.Band5Address
                    )
                if self._proxy_sw_1 is None:
                    self.logger.info("Connect to search window proxy device")
                    self._proxy_sw_1 = self._dev_factory.get_device(
                        self.SW1Address
                    )
                if self._proxy_sw_2 is None:
                    self.logger.info("Connect to search window proxy device")
                    self._proxy_sw_2 = self._dev_factory.get_device(
                        self.SW2Address
                    )
        except Exception as ex:
            self.logger.info(
                "Unexpected error on DeviceProxy creation %s", str(ex)
            )
        # PROTECTED REGION END #    //  Vcc.always_executed_hook

    def delete_device(self):
        """
        Hook to delete resources allocated in the
        :py:meth:`~.Vcc.InitCommand.do` method of
        the nested :py:class:`~.Vcc.InitCommand`
        class.

        This method allows for any memory or other resources allocated
        in the :py:meth:`~.Vcc.InitCommand.do` method to be
        released. This method is called by the device destructor, and by
        the Init command when the Tango device server is re-initialised.
        """
        pass

    # ------------------
    # Attributes methods
    # ------------------

    def read_receptorID(self):
        # PROTECTED REGION ID(Vcc.receptorID_read) ENABLED START #
        """Return recptorID attribut(int)"""
        return self._receptor_ID
        # PROTECTED REGION END #    //  Vcc.receptorID_read

    def write_receptorID(self, value):
        # PROTECTED REGION ID(Vcc.receptorID_write) ENABLED START #
        """Set receptor ID attribute(int)"""
        self._receptor_ID = value
        # PROTECTED REGION END #    //  Vcc.receptorID_write

    def read_subarrayMembership(self):
        # PROTECTED REGION ID(Vcc.subarrayMembership_read) ENABLED START #
        """Return subarrayMembership attribute: sub-array affiliation of the VCC(0 of no affliation)"""
        self.logger.debug("Entering read_subarrayMembership(), _subarray_membership = {}".format(self._subarray_membership))
        return self._subarray_membership
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_read

    def write_subarrayMembership(self, value):
        # PROTECTED REGION ID(Vcc.subarrayMembership_write) ENABLED START #
        """Set subarrayMembership attribute: sub-array affiliation of the VCC(0 of no affliation)"""
        self.logger.debug("Entering write_subarrayMembership(), value = {}".format(value))
        self._subarray_membership = value
        self.push_change_event("subarrayMembership",value)
        if not value:
            self._update_obs_state(ObsState.IDLE)
        # PROTECTED REGION END #    //  Vcc.subarrayMembership_write

    def read_frequencyBand(self):
        # PROTECTED REGION ID(Vcc.frequencyBand_read) ENABLED START #
        """Return frequencyBand attribute: frequency band being observed by the current scan (one of ["1", "2", "3", "4", "5a", "5b", ])"""
        return self._frequency_band
        # PROTECTED REGION END #    //  Vcc.frequencyBand_read

    def read_band5Tuning(self):
        # PROTECTED REGION ID(Vcc.band5Tuning_read) ENABLED START #
        """Return band5Tuning attribute: Stream tuning (GHz) in float"""
        return self._stream_tuning
        # PROTECTED REGION END #    //  Vcc.band5Tuning_read

    def write_band5Tuning(self, value):
        # PROTECTED REGION ID(Vcc.band5Tuning_write) ENABLED START #
        """Set band5Tuning attribute: Stream tuning (GHz) in float"""
        self._stream_tuning = value
        # PROTECTED REGION END #    //  Vcc.band5Tuning_write

    def read_frequencyBandOffsetStream1(self):
        # PROTECTED REGION ID(Vcc.frequencyBandOffsetStream1_read) ENABLED START #
        """Return frequecyBandOffsetStream1 attribute(int)"""
        return self._frequency_band_offset_stream_1
        # PROTECTED REGION END #    //  Vcc.frequencyBandOffsetStream1_read

    def write_frequencyBandOffsetStream1(self, value):
        # PROTECTED REGION ID(Vcc.frequencyBandOffsetStream1_write) ENABLED START #
        """Set frequecyBandOffsetStream1 attribute(int)"""
        self._frequency_band_offset_stream_1 = value
        # PROTECTED REGION END #    //  Vcc.frequencyBandOffsetStream1_write

    def read_frequencyBandOffsetStream2(self):
        # PROTECTED REGION ID(Vcc.frequencyBandOffsetStream2_read) ENABLED START #
        """Return frequecyBandOffsetStream2 attribute(int)"""
        return self._frequency_band_offset_stream_2
        # PROTECTED REGION END #    //  Vcc.frequencyBandOffsetStream2_read

    def write_frequencyBandOffsetStream2(self, value):
        # PROTECTED REGION ID(Vcc.frequencyBandOffsetStream2_write) ENABLED START #
        """Set frequecyBandOffsetStream2 attribute(int)"""
        self._frequency_band_offset_stream_2 = value
        # PROTECTED REGION END #    //  Vcc.frequencyBandOffsetStream2_write

    def read_dopplerPhaseCorrection(self):
        # PROTECTED REGION ID(Vcc.dopplerPhaseCorrection_read) ENABLED START #
        """Return dopplerPhaseCorrection attribute(float)"""
        return self._doppler_phase_correction
        # PROTECTED REGION END #    //  Vcc.dopplerPhaseCorrection_read

    def write_dopplerPhaseCorrection(self, value):
        # PROTECTED REGION ID(Vcc.dopplerPhaseCorrection_write) ENABLED START #
        """Set dopplerPhaseCorrection attribute(float)"""
        self._doppler_phase_correction = value
        # PROTECTED REGION END #    //  Vcc.dopplerPhaseCorrection_write

    def read_rfiFlaggingMask(self):
        # PROTECTED REGION ID(Vcc.rfiFlaggingMask_read) ENABLED START #
        """Return rfiFlaggingMask attribute(str/JSON)"""
        return self._rfi_flagging_mask
        # PROTECTED REGION END #    //  Vcc.rfiFlaggingMask_read

    def write_rfiFlaggingMask(self, value):
        # PROTECTED REGION ID(Vcc.rfiFlaggingMask_write) ENABLED START #
        """Set rfiFlaggingMask attribute(str/JSON)"""
        self._rfi_flagging_mask = value
        # PROTECTED REGION END #    //  Vcc.rfiFlaggingMask_write

    def read_scfoBand1(self):
        # PROTECTED REGION ID(Vcc.scfoBand1_read) ENABLED START #
        """Return scfoBand1 attribute(int): Sample clock frequency offset for band 1"""
        return self._scfo_band_1
        # PROTECTED REGION END #    //  Vcc.scfoBand1_read

    def write_scfoBand1(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand1_write) ENABLED START #
        """Set scfoBand1 attribute(int): Sample clock frequency offset for band 1"""
        self._scfo_band_1 = value
        # PROTECTED REGION END #    //  Vcc.scfoBand1_write

    def read_scfoBand2(self):
        # PROTECTED REGION ID(Vcc.scfoBand2_read) ENABLED START #
        """Return scfoBand2 attribute(int): Sample clock frequency offset for band 2"""
        return self._scfo_band_2
        # PROTECTED REGION END #    //  Vcc.scfoBand2_read

    def write_scfoBand2(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand2_write) ENABLED START #
        """Set scfoBand2 attribute(int): Sample clock frequency offset for band 2"""
        self._scfo_band_2 = value
        # PROTECTED REGION END #    //  Vcc.scfoBand2_write

    def read_scfoBand3(self):
        # PROTECTED REGION ID(Vcc.scfoBand3_read) ENABLED START #
        """Return scfoBand3 attribute(int): Sample clock frequency offset for band 3"""        
        return self._scfo_band_3
        # PROTECTED REGION END #    //  Vcc.scfoBand3_read

    def write_scfoBand3(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand3_write) ENABLED START #
        """Set scfoBand3 attribute(int): Sample clock frequency offset for band 3"""        
        self._scfo_band_3 = value
        # PROTECTED REGION END #    //  Vcc.scfoBand3_write

    def read_scfoBand4(self):
        # PROTECTED REGION ID(Vcc.scfoBand4_read) ENABLED START #
        """Return scfoBand4 attribute(int): Sample clock frequency offset for band 4"""        
        return self._scfo_band_4
        # PROTECTED REGION END #    //  Vcc.scfoBand4_read

    def write_scfoBand4(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand4_write) ENABLED START #
        """Set scfoBand4 attribute(int): Sample clock frequency offset for band 4"""        
        self._scfo_band_4 = value
        # PROTECTED REGION END #    //  Vcc.scfoBand4_write

    def read_scfoBand5a(self):
        # PROTECTED REGION ID(Vcc.scfoBand5a_read) ENABLED START #
        """Return scfoBand5a attribute(int): Sample clock frequency offset for band 5a"""        
        return self._scfo_band_5a
        # PROTECTED REGION END #    //  Vcc.scfoBand5a_read

    def write_scfoBand5a(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand5a_write) ENABLED START #
        """Set scfoBand5a attribute(int): Sample clock frequency offset for band 5a"""        
        self._scfo_band_5a = value
        # PROTECTED REGION END #    //  Vcc.scfoBand5a_write

    def read_scfoBand5b(self):
        # PROTECTED REGION ID(Vcc.scfoBand5b_read) ENABLED START #
        """Return scfoBand5b attribute(int): Sample clock frequency offset for band 5b"""        
        return self._scfo_band_5b
        # PROTECTED REGION END #    //  Vcc.scfoBand5b_read

    def write_scfoBand5b(self, value):
        # PROTECTED REGION ID(Vcc.scfoBand5b_write) ENABLED START #
        """Set scfoBand5b attribute(int): Sample clock frequency offset for band 5b"""        
        self._scfo_band_5b = value
        # PROTECTED REGION END #    //  Vcc.scfoBand5b_write

    def read_delayModel(self):
        # PROTECTED REGION ID(Vcc.delayModel_read) ENABLED START #
        """Return delayModel attribute(2 dim, max=6*26 array): Delay model coefficients, given per frequency slice"""
        return self._delay_model
        # PROTECTED REGION END #    //  Vcc.delayModel_read

    def read_jonesMatrix(self):
        # PROTECTED REGION ID(Vcc.jonesMatrix_read) ENABLED START #
        """Return jonesMatrix attribute(max=16 array): Jones Matrix, given per frequency slice"""
        return self._jones_matrix
        # PROTECTED REGION END #    //  Vcc.jonesMatrix_read

    def read_scanID(self):
        # PROTECTED REGION ID(Vcc.scanID_read) ENABLED START #
        """Return the scanID attribute."""
        return self._scan_id
        # PROTECTED REGION END #    //  Vcc.scanID_read

    def write_scanID(self, value):
        # PROTECTED REGION ID(Vcc.scanID_write) ENABLED START #
        """Set the scanID attribute."""
        self._scan_id=value
        # PROTECTED REGION END #    //  Vcc.scanID_write

    def read_configID(self):
        # PROTECTED REGION ID(Vcc.configID_read) ENABLED START #
        """Return the configID attribute."""
        return self._config_id
        # PROTECTED REGION END #    //  Vcc.configID_read

    def write_configID(self, value):
        # PROTECTED REGION ID(Vcc.configID_write) ENABLED START #
        """Set the configID attribute."""
        self._config_id = value
        # PROTECTED REGION END #    //  Vcc.configID_write

    # --------
    # Commands
    # --------

    class ConfigureScanCommand(CspSubElementObsDevice.ConfigureScanCommand):
        """
        A class for the Vcc's ConfigureScan() command.
        """

        def do(self, argin):
            """
            Stateless hook for ConfigureScan() command functionality.

            :param argin: The configuration as JSON formatted string
            :type argin: str

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            :raises: ``CommandError`` if the configuration data validation fails.
            """

            self.logger.debug("Entering ConfigureScanCommand()")

            device = self.target

            # By this time, the receptor_ID should be set:
            self.logger.debug(("device._receptor_ID = {}".
            format(device._receptor_ID)))

            # validate the input args
            (result_code, msg) = self.validate_input(argin)

            if result_code == ResultCode.OK:
                # TODO: cosider to turn_on the selected band device
                #       via a separate command
                if Vcc.TEST_CONTEXT is False:
                    self.turn_on_band_device(device._freq_band_name)
                # store the configuration on command success
                device._last_scan_configuration = argin
                msg = "Configure command completed OK"

            return(result_code, msg)
            
        def validate_input(self, argin):
            """
            Validate the configuration parameters against allowed values, as needed.

            :param argin: The JSON formatted string with configuration for the device.
            :type argin: 'DevString'
            :return: A tuple containing a return code and a string message.
            :rtype: (ResultCode, str)
            """
            device = self.target

            try:
                config_dict = json.loads(argin)
                device._config_id = config_dict['config_id']

                freq_band_name = config_dict['frequency_band']
                device._freq_band_name = freq_band_name
                device._frequency_band = freq_band_dict()[freq_band_name]

                # call the method to validate the data sent with
                # the configuration, as needed.
                return (ResultCode.OK, "ConfigureScan arguments validation successfull")

            except (KeyError, json.JSONDecodeError) as err:
                msg = "Validate configuration failed with error:{}".format(err)
            except Exception as other_errs:
                msg = "Validate configuration failed with unknown error:{}".format(
                    other_errs)
                self.logger.error(msg)
            return (ResultCode.FAILED, msg)

        def turn_on_band_device(self, freq_band_name):
            """
            Constraint: Must be called AFTER validate_input()
            Set corresponding band of this VCC. # TODO - remove this
            Send ON signal to the corresponding band, and DISABLE signal 
            to all others
            """

            device = self.target

            # TODO: can be done in a more Pythonian way; broken?
            if freq_band_name in ["1", "2"]:
                device._proxy_band_12.On()
                device._proxy_band_3.Disable()
                device._proxy_band_4.Disable()
                device._proxy_band_5.Disable()
            elif freq_band_name == "3":
                device._proxy_band_12.Disable()
                device._proxy_band_3.On()
                device._proxy_band_4.Disable()
                device._proxy_band_5.Disable()
            elif freq_band_name == "4":
                device._proxy_band_12.Disable()
                device._proxy_band_3.Disable()
                device._proxy_band_4.On()
                device._proxy_band_5.Disable()
            elif freq_band_name in ["5a", "5b"]:
                device._proxy_band_12.Disable()
                device._proxy_band_3.Disable()
                device._proxy_band_4.Disable()
                device._proxy_band_5.On()
            else:
                # The frequnecy band name has been validated at this point
                # so this shouldn't happen
                pass

    @command(
        dtype_in='DevString',
        doc_in="JSON formatted string with the scan configuration.",
        dtype_out='DevVarLongStringArray',
        doc_out="A tuple containing a return code and a string message indicating status. "
                "The message is for information purpose only.",
    )
    @DebugIt()
    def ConfigureScan(self, argin):
        # PROTECTED REGION ID(Vcc.ConfigureScan) ENABLED START #
        """
        Configure the observing device parameters for the current scan.

        :param argin: JSON formatted string with the scan configuration.
        :type argin: 'DevString'

        :return: A tuple containing a return code and a string message indicating status.
            The message is for information purpose only.
        :rtype: (ResultCode, str)
        """
        command = self.get_command_object("ConfigureScan")
        (return_code, message) = command(argin)
        return [[return_code], [message]]
        # PROTECTED REGION END #    //  Vcc.ConfigureScan

    class GoToIdleCommand(CspSubElementObsDevice.GoToIdleCommand):
        """
        A class for the Vcc's GoToIdle command.
        """

        def do(self):
            """
            Stateless hook for GoToIdle() command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            self.logger.debug("Entering GoToIdleCommand()")

            device = self.target

            # Reset all values intialized in InitCommand.do():

            device._freq_band_name = ""
            device._frequency_band = 0
            
            # device._receptor_ID  - DO NOT reset!
            # _receptor_ID is set via an explicit write
            # BEFORE ConfigureScan() is executed; 

            # device._subarray_membership -  DO NOT reset! 
            
            device._stream_tuning = (0, 0)
            device._frequency_band_offset_stream_1 = 0
            device._frequency_band_offset_stream_2 = 0
            device._doppler_phase_correction = (0, 0, 0, 0)
            device._rfi_flagging_mask = ""
            device._scfo_band_1 = 0
            device._scfo_band_2 = 0
            device._scfo_band_3 = 0
            device._scfo_band_4 = 0
            device._scfo_band_5a = 0
            device._scfo_band_5b = 0
            device._delay_model = [[0] * 6 for i in range(26)]
            device._jones_matrix = [[0] * 16 for i in range(26)]

            device._scan_id = 0
            device._config_id = ""

            if device.state_model.obs_state == ObsState.IDLE:
                return (ResultCode.OK, 
                "GoToIdle command completed OK. Device already IDLE")

            return (ResultCode.OK, "GoToIdle command completed OK")

    def is_UpdateDelayModel_allowed(self):
        """allowed when Devstate is ON and ObsState is READY OR SCANNIGN"""
        self.logger.debug("Entering is_UpdateDelayModel_allowed()")
        self.logger.debug("self._obs_state = {}.format(self.dev_state())")
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state in [ObsState.READY, ObsState.SCANNING]:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Delay model, given per frequency slice"
    )
    def UpdateDelayModel(self, argin):
        # PROTECTED REGION ID(Vcc.UpdateDelayModel) ENABLED START #
        """update VCC's delay model(serialized JSON object)"""

        self.logger.debug("Entering UpdateDelayModel()")
        argin = json.loads(argin)

        self.logger.debug(("self._receptor_ID = {}".
            format(self._receptor_ID)))

        for delayDetails in argin:
            self.logger.debug(("delayDetails[receptor] = {}".
            format(delayDetails["receptor"])))

            if delayDetails["receptor"] != self._receptor_ID:
                continue
            for frequency_slice in delayDetails["receptorDelayDetails"]:
                if 1 <= frequency_slice["fsid"] <= 26:
                    if len(frequency_slice["delayCoeff"]) == 6:
                        self._delay_model[frequency_slice["fsid"] - 1] = \
                            frequency_slice["delayCoeff"]
                    else:
                        log_msg = "'delayCoeff' not valid for frequency slice {} of " \
                                    "receptor {}".format(frequency_slice["fsid"], self._receptor_ID)
                        self.logger.error(log_msg)
                else:
                    log_msg = "'fsid' {} not valid for receptor {}".format(
                        frequency_slice["fsid"], self._receptor_ID
                    )
                    self.logger.error(log_msg)
        # PROTECTED REGION END #    // Vcc.UpdateDelayModel

    def is_UpdateJonesMatrix_allowed(self):
        """allowed when Devstate is ON and ObsState is READY OR SCANNINNG"""
        if self.dev_state() == tango.DevState.ON and \
                self._obs_state in [ObsState.READY, ObsState.SCANNING]:
            return True
        return False

    @command(
        dtype_in='str',
        doc_in="Jones Matrix, given per frequency slice"
    )
    def UpdateJonesMatrix(self, argin):
        # PROTECTED REGION ID(Vcc.UpdateJonesMatrix) ENABLED START #
        self.logger.debug("Vcc.UpdateJonesMatrix")
        """update FSP's Jones matrix (serialized JSON object)"""

        argin = json.loads(argin)

        for receptor in argin:
            if receptor["receptor"] == self._receptor_ID:
                for frequency_slice in receptor["receptorMatrix"]:
                    fs_id = frequency_slice["fsid"]
                    matrix = frequency_slice["matrix"]
                    if 1 <= fs_id <= 26:
                        if len(matrix) == 16:
                            self._jones_matrix[fs_id-1] = matrix.copy()
                        else:
                            log_msg = "'matrix' not valid for frequency slice {} of " \
                                      "receptor {}".format(fs_id, self._receptor_ID)
                            self.logger.error(log_msg)
                    else:
                        log_msg = "'fsid' {} not valid for receptor {}".format(
                            fs_id, self._receptor_ID
                        )
                        self.logger.error(log_msg)
        # PROTECTED REGION END #    // Vcc.UpdateJonesMatrix

    def is_ValidateSearchWindow_allowed(self):
        # This command has no constraints:
        return True

    @command(
        dtype_in='str',
        doc_in='JSON object to configure a search window'
    )
    def ValidateSearchWindow(self, argin):
        """validate a search window configuration. The input is JSON object with the search window parameters. Called by the subarray"""
        # try to deserialize input string to a JSON object

        self.logger.debug("Entering ValidateSearchWindow()") 

        try:
            argin = json.loads(argin)
        except json.JSONDecodeError:  # argument not a valid JSON object
            msg = "Search window configuration object is not a valid JSON object."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                         tango.ErrSeverity.ERR)

        # Validate searchWindowID.
        if "search_window_id" in argin:
            if int(argin["search_window_id"]) in [1, 2]:
                pass
            else:  # searchWindowID not in valid range
                msg = "'searchWindowID' must be one of [1, 2] (received {}).".format(
                    str(argin["search_window_id"])
                )
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)
        else:
            msg = "Search window specified, but 'searchWindowID' not given."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                         tango.ErrSeverity.ERR)

        # Validate searchWindowTuning.
        if "search_window_tuning" in argin:
            freq_band_name = argin["frequency_band"]
            if freq_band_name not in ["5a", "5b"]:  # frequency band is not band 5
                
                frequencyBand_mi = freq_band_dict()[freq_band_name]
                
                frequencyBand = ["1", "2", "3", "4", "5a", "5b"].index(argin["frequency_band"])

                assert frequencyBand_mi == frequencyBand
                
                start_freq_Hz, stop_freq_Hz = [
                    const.FREQUENCY_BAND_1_RANGE_HZ,
                    const.FREQUENCY_BAND_2_RANGE_HZ,
                    const.FREQUENCY_BAND_3_RANGE_HZ,
                    const.FREQUENCY_BAND_4_RANGE_HZ
                ][frequencyBand]

                self.logger.debug("start_freq_Hz = {}".format(start_freq_Hz)) 
                self.logger.debug("stop_freq_Hz = {}".format(stop_freq_Hz)) 

                if start_freq_Hz + argin["frequency_band_offset_stream_1"] <= \
                        int(argin["search_window_tuning"]) <= \
                        stop_freq_Hz + argin["frequency_band_offset_stream_1"]:
                    pass
                else:
                    msg = "'searchWindowTuning' must be within observed band."
                    self.logger.error(msg)
                    tango.Except.throw_exception("Command failed", msg,
                                                 "ConfigureSearchWindow execution",
                                                 tango.ErrSeverity.ERR)
            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                if argin["band_5_tuning"] == [0,0]: # band 5 tuning not specified in configuration
                    pass
                else:
                    frequency_band_range_1 = (
                        argin["band_5_tuning"][0] * 10 ** 9 + argin["frequency_band_offset_stream_1"] - \
                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                        argin["band_5_tuning"][0] * 10 ** 9 + argin["frequency_band_offset_stream_1"] + \
                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                    )

                    frequency_band_range_2 = (
                        argin["band_5_tuning"][1] * 10 ** 9 + argin["frequency_band_offset_stream_2"] - \
                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                        argin["band_5_tuning"][1] * 10 ** 9 + argin["frequency_band_offset_stream_2"] + \
                        const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                    )

                    if (frequency_band_range_1[0] <= \
                        int(argin["search_window_tuning"]) <= \
                        frequency_band_range_1[1]) or \
                            (frequency_band_range_2[0] <= \
                            int(argin["search_window_tuning"]) <= \
                            frequency_band_range_2[1]):
                        pass
                    else:
                        msg = "'searchWindowTuning' must be within observed band."
                        self.logger.error(msg)
                        tango.Except.throw_exception("Command failed", msg,
                                                    "ConfigureSearchWindow execution",
                                                    tango.ErrSeverity.ERR)
        else:
            msg = "Search window specified, but 'searchWindowTuning' not given."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                         tango.ErrSeverity.ERR)

        # Validate tdcEnable.
        if "tdc_enable" in argin:
            if argin["tdc_enable"] in [True, False]:
                pass
            else:
                msg = "Search window specified, but 'tdcEnable' not given."
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)
        else:
            msg = "Search window specified, but 'tdcEnable' not given."
            self.logger.error(msg)
            tango.Except.throw_exception("Command failed", msg, "ConfigureSearchWindow execution",
                                         tango.ErrSeverity.ERR)

        # Validate tdcNumBits.
        if argin["tdc_enable"]:
            if "tdc_num_bits" in argin:
                if int(argin["tdc_num_bits"]) in [2, 4, 8]:
                    pass
                else:
                    msg = "'tdcNumBits' must be one of [2, 4, 8] (received {}).".format(
                        str(argin["tdc_num_bits"])
                    )
                    self.logger.error(msg)
                    tango.Except.throw_exception("Command failed", msg,
                                                 "ConfigureSearchWindow execution",
                                                 tango.ErrSeverity.ERR)
            else:
                msg = "Search window specified with TDC enabled, but 'tdcNumBits' not given."
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)

        # Validate tdcPeriodBeforeEpoch.
        if "tdc_period_before_epoch" in argin:
            if int(argin["tdc_period_before_epoch"]) > 0:
                pass
            else:
                msg = "'tdcPeriodBeforeEpoch' must be a positive integer (received {}).".format(
                    str(argin["tdc_period_before_epoch"])
                )
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)
        else:
            pass

        # Validate tdcPeriodAfterEpoch.
        if "tdc_period_after_epoch" in argin:
            if int(argin["tdc_period_after_epoch"]) > 0:
                pass
            else:
                msg = "'tdcPeriodAfterEpoch' must be a positive integer (received {}).".format(
                    str(argin["tdc_period_after_epoch"])
                )
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)
        else:
            pass

        # Validate tdcDestinationAddress.
        if argin["tdc_enable"]:
            try:
                for receptor in argin["tdc_destination_address"]:
                    if int(receptor["receptor_id"]) == self._receptor_ID:
                    # TODO: validate input
                        break
                    else:  # receptorID not found
                        raise KeyError  # just handle all the errors in one place
            except KeyError:
                # tdcDestinationAddress not given or receptorID not in tdcDestinationAddress
                msg = "Search window specified with TDC enabled, but 'tdcDestinationAddress' " \
                      "not given or missing receptors."
                self.logger.error(msg)
                tango.Except.throw_exception("Command failed", msg,
                                             "ConfigureSearchWindow execution",
                                             tango.ErrSeverity.ERR)

    def is_ConfigureSearchWindow_allowed(self):
        """allowed if DevState is ON and ObsState is CONFIGURING"""
        if self.dev_state() == tango.DevState.ON and \
            (self._obs_state == ObsState.CONFIGURING or \
            self._obs_state == ObsState.READY):
            return True
        return False

    @command(
        dtype_in='str',
        doc_in='JSON object to configure a search window'
    )
    def ConfigureSearchWindow(self, argin):
        # PROTECTED REGION ID(Vcc.ConfigureSearchWindow) ENABLED START #
        # 
        """
        configure SearchWindow by sending parameters from the input(JSON) to SearchWindow device.
        This function is called by the subarray after the configuration has already been validated, so the checks here have been removed to reduce overhead.
        """

        self.logger.debug("Entering ConfigureSearchWindow()") 
        argin = json.loads(argin)

        # variable to use as SW proxy
        proxy_sw = None

        # Configure searchWindowID.
        #TODO: remove temporary flag to disable Vcc proxies for unit testing
        if Vcc.TEST_CONTEXT is False:
            if int(argin["search_window_id"]) == 1:
                proxy_sw = self._proxy_sw_1
            elif int(argin["search_window_id"]) == 2:
                proxy_sw = self._proxy_sw_2

            # Configure searchWindowTuning.
            if self._frequency_band in list(range(4)):  # frequency band is not band 5
                proxy_sw.searchWindowTuning = argin["search_window_tuning"]

                start_freq_Hz, stop_freq_Hz = [
                    const.FREQUENCY_BAND_1_RANGE_HZ,
                    const.FREQUENCY_BAND_2_RANGE_HZ,
                    const.FREQUENCY_BAND_3_RANGE_HZ,
                    const.FREQUENCY_BAND_4_RANGE_HZ
                ][self._frequency_band]

                if start_freq_Hz + self._frequency_band_offset_stream_1 + \
                        const.SEARCH_WINDOW_BW_HZ / 2 <= \
                        int(argin["search_window_tuning"]) <= \
                        stop_freq_Hz + self._frequency_band_offset_stream_1 - \
                        const.SEARCH_WINDOW_BW_HZ / 2:
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = "'searchWindowTuning' partially out of observed band. " \
                            "Proceeding."
                    self.logger.warn(log_msg)
            else:  # frequency band 5a or 5b (two streams with bandwidth 2.5 GHz)
                proxy_sw.searchWindowTuning = argin["search_window_tuning"]

                frequency_band_range_1 = (
                    self._stream_tuning[0] * 10 ** 9 + self._frequency_band_offset_stream_1 - \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                    self._stream_tuning[0] * 10 ** 9 + self._frequency_band_offset_stream_1 + \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                )

                frequency_band_range_2 = (
                    self._stream_tuning[1] * 10 ** 9 + self._frequency_band_offset_stream_2 - \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2,
                    self._stream_tuning[1] * 10 ** 9 + self._frequency_band_offset_stream_2 + \
                    const.BAND_5_STREAM_BANDWIDTH * 10 ** 9 / 2
                )

                if (frequency_band_range_1[0] + \
                    const.SEARCH_WINDOW_BW * 10 ** 6 / 2 <= \
                    int(argin["search_window_tuning"]) <= \
                    frequency_band_range_1[1] - \
                    const.SEARCH_WINDOW_BW * 10 ** 6 / 2) or \
                        (frequency_band_range_2[0] + \
                        const.SEARCH_WINDOW_BW * 10 ** 6 / 2 <= \
                        int(argin["search_window_tuning"]) <= \
                        frequency_band_range_2[1] - \
                        const.SEARCH_WINDOW_BW * 10 ** 6 / 2):
                    # this is the acceptable range
                    pass
                else:
                    # log a warning message
                    log_msg = "'searchWindowTuning' partially out of observed band. " \
                            "Proceeding."
                    self.logger.warn(log_msg)

            # Configure tdcEnable.
            proxy_sw.tdcEnable = argin["tdc_enable"]
            if argin["tdc_enable"]:
                proxy_sw.On()
            else:
                proxy_sw.Disable()

            # Configure tdcNumBits.
            if argin["tdc_enable"]:
                proxy_sw.tdcNumBits = int(argin["tdc_num_bits"])

            # Configure tdcPeriodBeforeEpoch.
            if "tdc_period_before_epoch" in argin:
                proxy_sw.tdcPeriodBeforeEpoch = int(argin["tdc_period_before_epoch"])
            else:
                proxy_sw.tdcPeriodBeforeEpoch = 2
                log_msg = "Search window specified, but 'tdcPeriodBeforeEpoch' not given. " \
                        "Defaulting to 2."
                self.logger.warn(log_msg)

            # Configure tdcPeriodAfterEpoch.
            if "tdc_period_after_epoch" in argin:
                proxy_sw.tdcPeriodAfterEpoch = int(argin["tdc_period_after_epoch"])
            else:
                proxy_sw.tdcPeriodAfterEpoch = 22
                log_msg = "Search window specified, but 'tdcPeriodAfterEpoch' not given. " \
                        "Defaulting to 22."
                self.logger.warn(log_msg)

            # Configure tdcDestinationAddress.
            if argin["tdc_enable"]:
                for receptor in argin["tdc_destination_address"]:
                    if int(receptor["receptor_id"]) == self._receptor_ID:
                        # TODO: validate input
                        proxy_sw.tdcDestinationAddress = \
                            receptor["tdc_destination_address"]
                        break

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(Vcc.main) ENABLED START #
    return run((Vcc,), args=args, **kwargs)
    # PROTECTED REGION END #    //  Vcc.main

if __name__ == '__main__':
    main()
