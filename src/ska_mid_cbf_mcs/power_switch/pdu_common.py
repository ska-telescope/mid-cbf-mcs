from __future__ import annotations

from ska_tango_base.control_model import PowerMode


class Outlet:
    """Represents a single outlet in the power switch."""

    def __init__(
        self: Outlet, outlet_ID: str, outlet_name: str, power_mode: PowerMode
    ) -> None:
        """
        Initialize a new instance.

        :param outlet_ID: ID of the outlet
        :param outlet_name: name of the outlet
        :param power_mode: current power mode of the outlet
        """
        self.outlet_ID = outlet_ID
        self.outlet_name = outlet_name
        self.power_mode = power_mode

        self.power_mode_str_dict = {
            PowerMode.UNKNOWN: "UNKNOWN",
            PowerMode.OFF: "OFF",
            PowerMode.STANDBY: "STANDBY",
            PowerMode.ON: "ON",
        }

    def __str__(self):
        return f"ID: {self.outlet_ID}; Name: {self.outlet_name}; mode: {self.power_mode_str_dict[self.power_mode]}"

    def __repr__(self):
        return self.__str__()
