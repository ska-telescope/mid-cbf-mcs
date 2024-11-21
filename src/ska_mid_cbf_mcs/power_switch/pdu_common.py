from __future__ import annotations

from ska_control_model import PowerState


class Outlet:
    """Represents a single outlet in the power switch."""

    def __init__(
        self: Outlet, outlet_ID: str, outlet_name: str, power_state: PowerState
    ) -> None:
        """
        Initialize a new instance.

        :param outlet_ID: ID of the outlet
        :param outlet_name: name of the outlet
        :param power_state: current power state of the outlet
        """
        self.outlet_ID = outlet_ID
        self.outlet_name = outlet_name
        self.power_state = power_state

    def __str__(self):
        return f"ID: {self.outlet_ID}; Name: {self.outlet_name}; state: {self.power_state.name}"

    def __repr__(self):
        return self.__str__()
