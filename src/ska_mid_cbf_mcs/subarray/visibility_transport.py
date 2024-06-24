"""
The Visibility Transport class controls the HPS device servers responsible for
routing the visibilties from FSPs to SDP. 

It is assumed that TalonDX boards will only be used in Mid-CBF up to AA1, 
supporting up to 8 boards. 
"""
from tango import DevFailed, DeviceProxy
from tango.Except import throw_exception

from ska_mid_cbf_mcs.slim.slim_config import SlimConfig


class VisibilityTransport:
    # number of fine channels in a output stream. Each FSP has 744 channel groups,
    # so 744 * 20 = 14880 fine channels.
    CHANNELS_PER_STREAM = 20

    def __init__(self):
        """
        Constructor
        """
        # Tango device proxies
        self._host_lut_s1_fqdns = []
        self._host_lut_s2_fqdn = None
        self._spead_desc_fqdns = None
        self._dp_host_lut_s1 = []
        self._dp_host_lut_s2 = None
        self._dp_spead_desc = None

        self._channel_offsets = []
        self._fsp_config = None

    def configure(self, fsp_config, vis_slim_yaml: str) -> None:
        """
        Configure the visibility transport devices.
        - determine which board is responsible for outputting visibilities
        - connect the host lut s1 devices to the host lut s2
        - write the channel offsets of each FSP to host lut s2
        - configure all the spead descriptor DS's

        :param fsp_config: FSP part of the scan configuration json object
        :param vis_slim_yaml: the visibility mesh config yaml
        :param board_to_fsp_id: a dict to convert talon board str to fsp ID
        :raise Tango exception: if the error occurs
        """
        self._fsp_ids = [fc["fsp_id"] for fc in fsp_config]
        self._channel_offsets = [fc["channel_offset"] for fc in fsp_config]
        self._host_lut_s1_fqdns = [
            f"talondx-00{id}/dshostlutstage1/host_lut_s1"
            for id in self._fsp_ids
        ]

        # Parse the visibility SLIM yaml to determine which board will output
        # visibilities
        vis_out_board = self._get_vis_output_board(vis_slim_yaml)
        self._host_lut_s2_fqdn = f"{vis_out_board}/dshostlutstage2/host_lut_s2"
        self._spead_desc_fqdn = f"{vis_out_board}/dsspeaddescriptor/spead"

        # Create device proxies
        self._dp_host_lut_s1 = [
            DeviceProxy(fqdn) for fqdn in self._host_lut_s1_fqdns
        ]
        self._dp_host_lut_s2 = DeviceProxy(self._host_lut_s2_fqdn)
        self._dp_spead_desc = DeviceProxy(self._spead_desc_fqdn)

        # connect the host lut s1 devices to the host lut s2
        for s1_dp, ch_offset in zip(
            self._dp_host_lut_s1, self._channel_offsets
        ):
            s1_dp.host_lut_stage_2_device_name = self._host_lut_s2_fqdn
            s1_dp.channel_offset = ch_offset
            s1_dp.connectToHostLUTStage2()

        # write the channel offsets of each FSP to host lut s2
        self._dp_host_lut_s2.host_lut_s1_chan_offsets = self._channel_offsets

        self._fsp_config = fsp_config

    def enable_output(
        self,
        subarray_id: int,
    ) -> None:
        """
        Enable the output of visibilities. This should be called after
        the FSP App on HPS has finished the scan command. This function does
        the following.
        - start sending SPEAD descriptors
        - program the host lut s2 device
        - program all the host lut s1 devices

        :param fsp_config: FSP part of the scan configuration json object
        :param n_vcc: number of receptors
        :param scan_id: the scan ID
        :raise Tango exception: if the error occurs
        """
        subarray_out_info = {"subarray_id": subarray_id}
        dest_host_data = self._parse_visibility_transport_info(
            self._fsp_config
        )
        subarray_out_info["dest_host_data"] = dest_host_data
        program_arg = {"Subarrays": subarray_out_info}

        # FSP App is responsible for calling the "Configure" command.
        # If not already called, StartScan will fail.
        self._dp_spead_desc.command_inout("StartScan", program_arg)

        self._dp_host_lut_s2.command_inout("Program", program_arg)

        for dp in self._dp_host_lut_s1:
            dp.command_inout("Program")

    def disable_output(self):
        """
        Disable the output of visibilities
        - Issue EndScan command to SPEAD Descriptor DS
        - Unprogram all the host lut s1 devices
        - Unprogram the host lut s2 device

        :raise Tango exception: if the configuration is not valid yaml, or
                                configuration is not valid.
        """
        self._dp_spead_desc.command_inout("EndScan")
        for dp in self._dp_host_lut_s1:
            dp.command_inout("Unprogram")
        self._dp_host_lut_s2.command_inout("Unprogram")

    def _parse_visibility_transport_info(self, fsp_config):
        """
        output_hosts are in format [[channel_id, ip_addr]]
        output_ports are in format [[channel_id, port]]

        Need to match the two by channel_id to get a list of [[ip_addr, port]]
        """
        out = []

        # Merge the output hosts and ports from FSP entries to one
        output_hosts = []
        output_ports = []
        min_offset = min(self._channel_offsets)
        for fsp in fsp_config:
            # the channel IDs are relative to the channel offset of the FSP entry
            diff = fsp["channel_offset"] - min_offset
            output_hosts += [[h[0] + diff, h[1]] for h in fsp["output_host"]]
            output_ports += [[p[0] + diff, p[1]] for p in fsp["output_port"]]

        next_host_idx = 1
        host_int = self._ip_to_int(output_hosts[0][1])
        for p in output_ports:
            if (
                next_host_idx < len(output_hosts)
                and output_hosts[next_host_idx][0] == p[0]
            ):
                host_int = self._ip_to_int(output_hosts[next_host_idx][1])
                next_host_idx += 1
            d = {}
            # TODO: why json???? The device servers should just take an array of integers
            d["chan_id"] = p[0] // 20
            d["ip_addr"] = host_int
            d["udp_port_num"] = p[1]
            out.append(d)
        return out

    def _ip_to_int(self, inet: str) -> int:
        return sum(
            [
                int(v) << (i * 8)
                for i, v in enumerate(reversed(inet.split(".")))
            ]
        )

    def _get_vis_output_board(self, vis_slim_yaml: str) -> str:
        """
        Determine the board to output visibilities

        :return: the TalonDX board ("talondx-00x") that will output visibilities
        :raise TangoException: if configuration is not valid
        """
        # TODO: This assumes only one board is used for output.
        #       This is sufficient for AA0.5. Need an update for AA1.
        vis_slim_yaml = self._proxy_vis_slim.meshConfiguration
        active_links = SlimConfig(vis_slim_yaml).active_links()
        rx0 = None
        for link in active_links:
            # extract only the "talondx-00x" part
            rx = link[1].split("/")[0]
            if rx0 is None:
                rx0 = rx
            else:
                if rx != rx0:
                    throw_exception(
                        "Visibility_Transport",
                        "Only one board can be used to output visibilities",
                        "_get_vis_output_board()",
                    )
        return rx0
