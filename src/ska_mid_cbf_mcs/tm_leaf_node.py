# -*- coding: utf-8 -*-
#
# This file is part of the TmCspSubarrayLeafNodeTest project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

from __future__ import annotations

from ska_tango_base.base.base_component_manager import BaseComponentManager
from ska_tango_base.base.base_device import SKABaseDevice
from tango.server import attribute

__all__ = ["TmCspSubarrayLeafNodeTest", "main"]


class TmCspSubarrayLeafNodeTest(SKABaseDevice):
    """
    TmCspSubarrayLeafNodeTest TANGO device class
    """

    # ------------------
    # Attributes methods
    # ------------------

    @attribute(
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
        self.logger.info(f"New delay model received: {value}")
        self._delay_model = value
        self.push_change_event("delayModel", value)
        self.push_archive_event("delayModel", value)

    # --------------
    # Initialization
    # --------------

    def init_device(self: TmCspSubarrayLeafNodeTest) -> None:
        """
        Override of init_device simply to setup attribute change events.
        """
        super().init_device()

        self._delay_model = ""
        self.set_change_event("delayModel", True)
        self.set_archive_event("delayModel", True)

    def create_component_manager(
        self: TmCspSubarrayLeafNodeTest,
    ) -> BaseComponentManager:
        """
        Create and return a component manager.

        :return: a component manager
        """
        return BaseComponentManager(logger=self.logger)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return TmCspSubarrayLeafNodeTest.run_server(args=args, **kwargs)


if __name__ == "__main__":
    main()
