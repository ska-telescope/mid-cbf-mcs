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

TmCspSubarrayLeafNodeTest TANGO device class for the CBF prototype
"""
from __future__ import annotations

from ska_tango_base.base.base_device import (
    DevVarLongStringArrayType,
    SKABaseDevice,
)
from tango.server import attribute

__all__ = ["TmCspSubarrayLeafNodeTest", "main"]


class TmCspSubarrayLeafNodeTest(SKABaseDevice):
    """
    TmCspSubarrayLeafNodeTest TANGO device class for the CBF prototype
    """

    # ------------------
    # Attributes methods
    # ------------------

    @attribute(
        abs_change=1,
        dtype="str",
        memorized=True,
        hw_memorized=True,
        doc="Delay model",
    )
    def delayModel(self: TmCspSubarrayLeafNodeTest) -> str:
        """
        Read the delayModel attribute.

        :return: current delayModel value
        :rtype: str
        """
        return self._delay_model

    @delayModel.write
    def delayModel(self: TmCspSubarrayLeafNodeTest, value: str) -> None:
        """
        Read the delayModel attribute.

        :param value: the delay model value
        """
        self._delay_model = value
        self.push_change_event("delayModel", value)

    # --------
    # Commands
    # --------

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the Fsp's init_device() "command".
        """

        def do(
            self: TmCspSubarrayLeafNodeTest.InitCommand,
            *args: any,
            **kwargs: any,
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """

            (result_code, message) = super().do(*args, **kwargs)

            self._delay_model = ""
            self.set_change_event("delayModel", True, True)

            return (result_code, message)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(TmCspSubarrayLeafNodeTest.main) ENABLED START #
    return TmCspSubarrayLeafNodeTest.run_server(args=args, **kwargs)
    # PROTECTED REGION END #    //  TmCspSubarrayLeafNodeTest.main


if __name__ == "__main__":
    main()
