# -*- coding: utf-8 -*-
#
# This file is part of the TmTelstateTest project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" TmTelstateTest Tango device prototype

TmTelstateTest TANGO device class for the CBF prototype
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
# PROTECTED REGION ID(CbfSubarray.additionnal_import) ENABLED START #
import os
import sys
import json

file_path = os.path.dirname(os.path.abspath(__file__))
commons_pkg_path = os.path.abspath(os.path.join(file_path, "../commons"))
sys.path.insert(0, commons_pkg_path)

from global_enum import HealthState, AdminMode
# PROTECTED REGION END #    //  TmTelstateTest.additionnal_import

__all__ = ["TmTelstateTest", "main"]


class TmTelstateTest(Device):
    """
    TmTelstateTest TANGO device class for the CBF prototype
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(TmTelstateTest.class_variable) ENABLED START #


    # PROTECTED REGION END #    //  TmTelstateTest.class_variable

    # -----------------
    # Device Properties
    # -----------------








    # ----------
    # Attributes
    # ----------

    dopplerPhaseCorrection_1 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 1)",
        doc="Doppler phase correction coefficients for subarray 1",
    )

    dopplerPhaseCorrection_2 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 2)",
        doc="Doppler phase correction coefficients for subarray 2",
    )

    dopplerPhaseCorrection_3 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 3)",
        doc="Doppler phase correction coefficients for subarray 3",
    )

    dopplerPhaseCorrection_4 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 4)",
        doc="Doppler phase correction coefficients for subarray 4",
    )

    dopplerPhaseCorrection_5 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 5)",
        doc="Doppler phase correction coefficients for subarray 5",
    )

    dopplerPhaseCorrection_6 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 6)",
        doc="Doppler phase correction coefficients for subarray 6",
    )

    dopplerPhaseCorrection_7 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 7)",
        doc="Doppler phase correction coefficients for subarray 7",
    )

    dopplerPhaseCorrection_8 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 8)",
        doc="Doppler phase correction coefficients for subarray 8",
    )

    dopplerPhaseCorrection_9 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 9)",
        doc="Doppler phase correction coefficients for subarray 9",
    )

    dopplerPhaseCorrection_10 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 10)",
        doc="Doppler phase correction coefficients for subarray 10",
    )

    dopplerPhaseCorrection_11 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 11)",
        doc="Doppler phase correction coefficients for subarray 11",
    )

    dopplerPhaseCorrection_12 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 12)",
        doc="Doppler phase correction coefficients for subarray 12",
    )

    dopplerPhaseCorrection_13 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 13)",
        doc="Doppler phase correction coefficients for subarray 13",
    )

    dopplerPhaseCorrection_14 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 14)",
        doc="Doppler phase correction coefficients for subarray 14",
    )

    dopplerPhaseCorrection_15 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 15)",
        doc="Doppler phase correction coefficients for subarray 15",
    )

    dopplerPhaseCorrection_16 = attribute(
        dtype=('float',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        label="Doppler phase correction (subarray 16)",
        doc="Doppler phase correction coefficients for subarray 16",
    )

    delayModel = attribute(
        dtype='str',
        access=AttrWriteType.READ_WRITE,
        label="Delay model coefficients",
        doc="Delay model coefficients, given per receptor per frequency slice per polarization, as a JSON object"
    )


    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        # PROTECTED REGION ID(TmTelstateTest.init_device) ENABLED START #
        self._doppler_phase_correction = [(0, 0, 0, 0) for i in range(16)]
        self._delay_model = {}  # this is interpreted as a JSON object
        # PROTECTED REGION END #    //  TmTelstateTest.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(TmTelstateTest.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TmTelstateTest.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(TmTelstateTest.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TmTelstateTest.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_dopplerPhaseCorrection_1(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_1_read) ENABLED START #
        return self._doppler_phase_correction[0]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_1_read

    def write_dopplerPhaseCorrection_1(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_1_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[0] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_1 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_1 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_1_write

    def read_dopplerPhaseCorrection_2(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_2_read) ENABLED START #
        return self._doppler_phase_correction[1]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_2_read

    def write_dopplerPhaseCorrection_2(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_2_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[1] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_2 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_2 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_2_write

    def read_dopplerPhaseCorrection_3(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_3_read) ENABLED START #
        return self._doppler_phase_correction[2]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_3_read

    def write_dopplerPhaseCorrection_3(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_3_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[2] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_3 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_3 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_3_write

    def read_dopplerPhaseCorrection_4(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_4_read) ENABLED START #
        return self._doppler_phase_correction[3]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_4_read

    def write_dopplerPhaseCorrection_4(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_4_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[3] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_4 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_4 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_4_write

    def read_dopplerPhaseCorrection_5(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_5_read) ENABLED START #
        return self._doppler_phase_correction[4]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_5_read

    def write_dopplerPhaseCorrection_5(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_5_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[4] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_5 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_5 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_5_write

    def read_dopplerPhaseCorrection_6(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_6_read) ENABLED START #
        return self._doppler_phase_correction[5]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_6_read

    def write_dopplerPhaseCorrection_6(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_6_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[5] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_6 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_6 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_6_write

    def read_dopplerPhaseCorrection_7(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_7_read) ENABLED START #
        return self._doppler_phase_correction[6]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_7_read

    def write_dopplerPhaseCorrection_7(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_7_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[6] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_7 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_7 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_7_write

    def read_dopplerPhaseCorrection_8(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_8_read) ENABLED START #
        return self._doppler_phase_correction[7]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_8_read

    def write_dopplerPhaseCorrection_8(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_8_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[7] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_8 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_8 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_8_write

    def read_dopplerPhaseCorrection_9(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_9_read) ENABLED START #
        return self._doppler_phase_correction[8]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_9_read

    def write_dopplerPhaseCorrection_9(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_9_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[8] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_9 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_9 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_9_write

    def read_dopplerPhaseCorrection_10(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_10_read) ENABLED START #
        return self._doppler_phase_correction[9]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_10_read

    def write_dopplerPhaseCorrection_10(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_10_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[9] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_10 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_10 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_10_write

    def read_dopplerPhaseCorrection_11(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_11_read) ENABLED START #
        return self._doppler_phase_correction[10]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_11_read

    def write_dopplerPhaseCorrection_11(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_11_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[10] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_11 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_11 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_11_write

    def read_dopplerPhaseCorrection_12(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_12_read) ENABLED START #
        return self._doppler_phase_correction[11]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_12_read

    def write_dopplerPhaseCorrection_12(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_12_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[11] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_12 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_12 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_12_write

    def read_dopplerPhaseCorrection_13(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_13_read) ENABLED START #
        return self._doppler_phase_correction[12]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_13_read

    def write_dopplerPhaseCorrection_13(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_13_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[12] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_13 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_13 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_13_write

    def read_dopplerPhaseCorrection_14(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_14_read) ENABLED START #
        return self._doppler_phase_correction[13]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_14_read

    def write_dopplerPhaseCorrection_14(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_14_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[13] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_14 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_14 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_14_write

    def read_dopplerPhaseCorrection_15(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_15_read) ENABLED START #
        return self._doppler_phase_correction[14]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_15_read

    def write_dopplerPhaseCorrection_15(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_15_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[14] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_15 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_15 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_15_write

    def read_dopplerPhaseCorrection_16(self):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_16_read) ENABLED START #
        return self._doppler_phase_correction[15]
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_16_read

    def write_dopplerPhaseCorrection_16(self, value):
        # PROTECTED REGION ID(TmTelstateTest.dopplerPhaseCorrection_16_write) ENABLED START #
        try:
            if len(value) == 4:
                self._doppler_phase_correction[15] = value
            else:
                log_msg = "Writing to dopplerPhaseCorrection_16 attribute expected 4 elements, \
                    but received {}. Ignoring.".format(len(value))
                self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        except TypeError:  # value is not an array
            log_msg = "dopplerPhaseCorrection_16 attribute must be an array of length 4. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.dopplerPhaseCorrection_16_write

    def read_delayModel(self):
        # PROTECTED REGION ID(TmTelstateTest.delayModel_read) ENABLED START #
        return json.dumps(self._delay_model)
        # PROTECTED REGION END #    //  TmTelstateTest.delayModel_read

    def write_delayModel(self, value):
        # PROTECTED REGION ID(TmTelstateTest.delayModel_write) ENABLED START #
        try:
            self._delay_model = json.loads(str(value))
        except Exception as e:  # value is not an array
            log_msg = "delayModel attribute must be a string representing a JSON object. Ignoring."
            self.dev_logging(log_msg, PyTango.LogLevel.LOG_ERROR)
        # PROTECTED REGION END #    //  TmTelstateTest.delayModel_write


    # --------
    # Commands
    # --------


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(TmTelstateTest.main) ENABLED START #
    return run((TmTelstateTest,), args=args, **kwargs)
    # PROTECTED REGION END #    //  TmTelstateTest.main

if __name__ == '__main__':
    main()
