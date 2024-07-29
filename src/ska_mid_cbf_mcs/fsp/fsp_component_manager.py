# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

import tango
from ska_control_model import AdminMode, PowerState, SimulationMode
from ska_tango_base.base.base_component_manager import check_communicating
from ska_tango_base.commands import ResultCode
from ska_tango_testing import context

from ska_mid_cbf_mcs.commons.global_enum import FspModes, const
from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.fsp.hps_fsp_controller_simulator import (
    HpsFspControllerSimulator,
)


class FspComponentManager(CbfComponentManager):
    """
    A component manager for the Fsp device.
    """

    def __init__(
        self: FspComponentManager,
        *args: any,
        fsp_id: int,
        all_fsp_corr_subarray_fqdn: list[str],
        # TODO: for Mid.CBF, to be updated to a list of FQDNs (max length = 20),
        # one entry for each Talon board in the FSP_UNIT
        hps_fsp_controller_fqdn: str,
        **kwargs: any,
    ) -> None:
        """
        Initialise a new instance.

        :param logger: a logger for this object to use
        :param fsp_id: the fsp id
        :param all_fsp_corr_subarray_fqdn: list of all
            fsp corr subarray fqdns
        # TODO: for Mid.CBF, param hps_fsp_controller_fqdn to be updated to a list of FQDNs (max length = 20), one entry for each Talon board in the FSP_UNIT
        :param hps_fsp_controller_fqdn: FQDN of the HPS FSP controller device
        """
        super().__init__(*args, **kwargs)

        self._fsp_id = fsp_id
        self._all_fsp_corr_subarray_fqdn = all_fsp_corr_subarray_fqdn
        self._hps_fsp_controller_fqdn = hps_fsp_controller_fqdn

        # Contains proxies to all FSP CORR devices
        self._all_fsp_corr = {}

        self._proxy_hps_fsp_controller = None

        self.subarray_membership = []
        self.function_mode = FspModes.IDLE.value  # IDLE

    # -------------
    # Communication
    # -------------

    def _start_communicating(
        self: FspComponentManager, *args, **kwargs
    ) -> None:
        """
        Establish communication with the component, then start monitoring.
        """
        for fqdn in self._all_fsp_corr_subarray_fqdn:
            try:
                self._all_fsp_corr[fqdn] = context.DeviceProxy(fqdn)
            except tango.DevFailed as df:
                self.logger.error(f"Failure in connecting to {fqdn}; {df}")
                self._update_communication_state(
                    communication_state=CommunicationStatus.NOT_ESTABLISHED
                )
                return

        super()._start_communicating()
        self._update_component_state(power=PowerState.OFF)

    # -------------
    # Fast Commands
    # -------------

    # --- On Command --- #

    @check_communicating
    def on(self: FspComponentManager) -> tuple[ResultCode, str]:
        """
        Establish communication with the FSP controller device on the HPS.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        # Try to connect to HPS devices, which are deployed during the
        # CbfController OnCommand sequence
        if self.simulation_mode == SimulationMode.FALSE:
            if self._proxy_hps_fsp_controller is None:
                try:
                    self._proxy_hps_fsp_controller = context.DeviceProxy(
                        device_name=self._hps_fsp_controller_fqdn
                    )
                except tango.DevFailed as df:
                    self.logger.error(
                        f"Failure in connection to HPS FSP controller; {df}"
                    )
                    self._update_communication_state(
                        communication_state=CommunicationStatus.NOT_ESTABLISHED
                    )
                    return (
                        ResultCode.FAILED,
                        "Failed to establish proxy to HPS FSP controller device",
                    )
        else:
            self._proxy_hps_fsp_controller = HpsFspControllerSimulator(
                self._hps_fsp_controller_fqdn,
            )

        self._update_component_state(power=PowerState.ON)
        return (ResultCode.OK, "On completed OK")

    # --- Off Command --- #

    @check_communicating
    def off(self: FspComponentManager) -> tuple[ResultCode, str]:
        """
        Cease communication with the FSP controller device on the HPS.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        self._proxy_hps_fsp_controller = None
        self._update_component_state(power=PowerState.OFF)
        return (ResultCode.OK, "Off completed OK")

    # --- SetFunctionMode Command --- #

    def _validate_and_set_function_mode(
        self: FspComponentManager, function_mode: str
    ) -> bool:
        """
        Sets functionMode attribute and pushes change event if valid, or return
        an error message if invalid.

        :param function_mode: function mode string to be evaluated
        :return: True if validation passes, otherwise False
        """
        # TODO: remove these conditions as new function modes are implemented
        if function_mode not in FspModes._member_names_ or function_mode in [
            "PSS-BF",
            "PST-BF",
            "VLBI",
        ]:
            self.logger.error(
                f"{function_mode} not a valid FSP function mode."
            )
            return False

        self.function_mode = FspModes[function_mode].value
        self._device_attr_change_callback("functionMode", self.function_mode)
        self._device_attr_archive_callback("functionMode", self.function_mode)
        self.logger.info(f"FSP set to function mode {function_mode}")

        return True

    def set_function_mode(
        self: FspComponentManager, function_mode: str
    ) -> None:
        """
        Switch the function mode of the FSP; can only be done if currently
        unassigned from any subarray membership.

        :param function_mode: one of 'IDLE','CORR','PSS-BF','PST-BF', or 'VLBI'

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        function_mode_success = self._validate_and_set_function_mode(
            function_mode
        )
        if not function_mode_success:
            return (
                ResultCode.FAILED,
                f"Failed to set FSP function mode to {function_mode}",
            )

        try:
            self._proxy_hps_fsp_controller.SetFunctionMode(self.function_mode)
        except tango.DevFailed as df:
            self.logger.error(f"{df.args[0].desc}")
            self._update_communication_state(
                communication_state=CommunicationStatus.NOT_ESTABLISHED
            )
            return (
                ResultCode.FAILED,
                "Failed to issue SetFunctionMode command to HPS FSP controller",
            )

        return (ResultCode.OK, "SetFunctionMode completed OK")

    # --- RemoveSubarrayMembership Command --- #

    def _subarray_off(self: FspComponentManager, subarray_id: int) -> bool:
        """
        Turn off FSP function mode subarray device for specified subarray

        :param subarray_id: ID of subarray for which to power off function mode proxy
        :return: False if unsuccessful in powering off FSP function mode subarray proxy,
            True otherwise
        """
        match self.function_mode:
            case FspModes.IDLE.value:
                self.logger.error(
                    f"FSP {self._fsp_id} function mode is IDLE, no subarray membership to remove."
                )

            case FspModes.CORR.value:
                fqdn = f"mid_csp_cbf/fspCorrSubarray/{self._fsp_id:02}_{subarray_id:02}"
                try:
                    proxy = self._all_fsp_corr[fqdn]
                    result = proxy.Off()
                    if result[0] == ResultCode.FAILED:
                        self.logger.error(
                            f"Failed to turn off {fqdn}; {result}"
                        )
                        return False
                except KeyError as ke:
                    self.logger.error(
                        f"FSP {self._fsp_id} CORR subarray {subarray_id} FQDN not found in properties; {ke}"
                    )
                    return False
                except tango.DevFailed as df:
                    self.logger.error(f"Failed to turn off {fqdn}; {df}")
                    return False
                return True

            case FspModes.PSS_BF.value:
                self.logger.error(
                    f"Error in removing subarray {subarray_id}; PSS-BF not currently implemented"
                )

            case FspModes.PST_BF.value:
                self.logger.error(
                    f"Error in removing subarray {subarray_id}; PST-BF not currently implemented"
                )

            case FspModes.VLBI.value:
                self.logger.error(
                    f"Error in removing subarray {subarray_id}; VLBI not currently implemented"
                )

        return False

    @check_communicating
    def remove_subarray_membership(
        self: FspComponentManager, subarray_id: int
    ) -> tuple[ResultCode, str]:
        """
        Remove subarray from the subarrayMembership list.
        If subarrayMembership is empty after removing
        (no subarray is using this FSP), set function mode to empty.

        :param subarray_id: an integer representing the subarray affiliation

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        if subarray_id not in self.subarray_membership:
            return (
                ResultCode.FAILED,
                f"FSP does not belong to subarray {subarray_id}",
            )

        self.logger.info(
            f"Removing subarray {subarray_id} from subarray membership."
        )

        off_success = self._subarray_off(subarray_id)
        if not off_success:
            return (
                ResultCode.FAILED,
                f"Unsuccessful in powering off function mode device for subarray {subarray_id}",
            )

        self.subarray_membership.remove(subarray_id)
        self._device_attr_change_callback(
            "subarrayMembership", self.subarray_membership
        )
        self._device_attr_archive_callback(
            "subarrayMembership", self.subarray_membership
        )

        # if no current subarray membership, reset to function mode IDLE and
        # power off
        if len(self.subarray_membership) == 0:
            self.logger.info(
                "No current subarray membership, resetting function mode to IDLE"
            )
            self._validate_and_set_function_mode("IDLE")
            self.off()

        return (
            ResultCode.OK,
            "RemoveSubarrayMembership completed OK",
        )

    # --- AddSubarrayMembership command --- #

    def _validate_subarray_id(
        self: FspComponentManager, subarray_id: int
    ) -> bool:
        """
        Validate subarray ID to be added to current membership.

        :param subarray_id: an integer representing the subarray affiliation,
            value in [1, 16]

        :return: True if subarray ID is valid, otherwise False
        """
        if len(self.subarray_membership) == const.MAX_SUBARRAY:
            self.logger.error(
                f"Fsp already assigned to the maximum number of subarrays ({const.MAX_SUBARRAY})"
            )
            return False
        if subarray_id - 1 not in range(const.MAX_SUBARRAY):
            self.logger.error(
                f"Subarray {subarray_id} invalid; must be in range [1, {const.MAX_SUBARRAY}]"
            )
            return False
        if subarray_id in self.subarray_membership:
            self.logger.error(f"FSP already belongs to subarray {subarray_id}")
            return False

        self.logger.info(
            f"Adding subarray {subarray_id} to subarray membership"
        )
        return True

    def _subarray_on(self: FspComponentManager, subarray_id: int) -> bool:
        """
        Turn on FSP function mode subarray device for specified subarray

        :param subarray_id: ID of subarray for which to power on function mode proxy
        :return: False if unsuccessful in powering on FSP function mode subarray proxy,
            True otherwise
        """
        match self.function_mode:
            case FspModes.IDLE.value:
                self.logger.error(
                    f"FSP {self._fsp_id} function mode is IDLE; error adding subarray {subarray_id} function mode device to group proxy."
                )

            case FspModes.CORR.value:
                # TODO: alternative to hardcoded FQDN?
                fqdn = f"mid_csp_cbf/fspCorrSubarray/{self._fsp_id:02}_{subarray_id:02}"
                try:
                    proxy = self._all_fsp_corr[fqdn]
                    # set FSP devices simulationMode attributes
                    self.toggle_simulation_mode(proxy, self.simulation_mode)
                    result = proxy.On()
                    if result[0] == ResultCode.FAILED:
                        self.logger.error(
                            f"Failed to turn on {fqdn}; {result}"
                        )
                        return False
                except KeyError as ke:
                    self.logger.error(
                        f"FSP {self._fsp_id} CORR subarray {subarray_id} FQDN not found in properties; {ke}"
                    )
                    return False
                except tango.DevFailed as df:
                    self.logger.error(f"Failed to turn on {fqdn}; {df}")
                    return False
                return True

            case FspModes.PSS_BF.value:
                self.logger.error(
                    f"Error in adding subarray {subarray_id}; PSS-BF not currently implemented"
                )

            case FspModes.PST_BF.value:
                self.logger.error(
                    f"Error in adding subarray {subarray_id}; PST-BF not currently implemented"
                )

            case FspModes.VLBI.value:
                self.logger.error(
                    f"Error in adding subarray {subarray_id}; VLBI not currently implemented"
                )

        return False

    @check_communicating
    def add_subarray_membership(
        self: FspComponentManager, subarray_id: int
    ) -> tuple[ResultCode, str]:
        """
        Add a subarray to the subarrayMembership list.

        :param subarray_id: an integer representing the subarray affiliation,
            value in [1, 16]

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        validate_success = self._validate_subarray_id(subarray_id)
        if not validate_success:
            return (
                ResultCode.FAILED,
                f"Unable to add subarray membership for subarray ID {subarray_id}",
            )

        on_success = self._subarray_on(subarray_id)
        if not on_success:
            return (
                ResultCode.FAILED,
                f"Unsuccessful in powering off function mode device for subarray {subarray_id}",
            )

        self.subarray_membership.append(subarray_id)
        self._device_attr_change_callback(
            "subarrayMembership", self.subarray_membership
        )
        self._device_attr_archive_callback(
            "subarrayMembership", self.subarray_membership
        )

        return (
            ResultCode.OK,
            "AddSubarrayMembership completed OK",
        )
