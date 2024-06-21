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

TmCspSubarrayLeafNodeTest Tango device prototype

TmCspSubarrayLeafNodeTest TANGO device class for the CBF prototype
"""

import os

from ska_tango_base.base.base_device import SKABaseDevice
from tango import AttrWriteType
from tango.server import attribute, run

file_path = os.path.dirname(os.path.abspath(__file__))


__all__ = ["TmCspSubarrayLeafNodeTest", "main"]


class TmCspSubarrayLeafNodeTest(SKABaseDevice):
    """
    TmCspSubarrayLeafNodeTest TANGO device class for the CBF prototype
    """

    # ----------
    # Attributes
    # ----------

    delayModel = attribute(
        dtype="str",
        access=AttrWriteType.READ_WRITE,
        label="Delay model coefficients",
        doc="Delay model coefficients",
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        super().init_device()
        self._delay_model = ""  # this is a JSON object as a string
        self.set_change_event("delayModel", True, True)

    # ------------------
    # Attributes methods
    # ------------------

    def read_delayModel(self):
        return self._delay_model

    def write_delayModel(self, value):
        self._delay_model = value
        self.push_change_event("delayModel", value)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return run((TmCspSubarrayLeafNodeTest,), args=args, **kwargs)


if __name__ == "__main__":
    main()
