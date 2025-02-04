import logging
import re

import tango
import yaml


class SlimConfig:
    def __init__(self, yaml_str: str, logger: logging.Logger):
        """
        Constructor

        :param yaml_str: the string defining the mesh links
        :param logger: the logger to use for logging
        :raise Tango exception: if the configuration is not valid yaml.
        """
        self.logger = logger
        self._active_links = self._parse_links_yaml(yaml_str)

    def active_links(self):
        """
        Returns the active links defined in the yaml file.

        :return: a list of HPS tx and rx device pairs as [Tx FQDN, Rx FQDN]
        :rtype: list[list[str]]
        """
        return self._active_links

    def get_unused_vis_rx(self) -> set[str]:
        """
        Determine the SLIM Rx devices that would receive data if loopback
        is enabled, but are not on the receiving end of any link in the
        visibilities mesh. We will need to disable loopback on these Rx
        to prevent visibilities being sent out of other FSP boards's 100g
        ethernet.

        For example, in the 2 FSP setup below, we need to disable loopback
        on talondx-002/slim-tx-rx/vis-rx0 because it will otherwise receive
        data from talondx-002/slim-tx-rx/vis-tx0, and send data out of talon
        002's 100g eth1.

        links_to_vis1:
            - talondx-001/slim-tx-rx/vis-tx0 -> talondx-001/slim-tx-rx/vis-rx0
            - talondx-002/slim-tx-rx/vis-tx0 -> talondx-001/slim-tx-rx/vis-rx1

        :return: a set of Rx FQDN on vis mesh that are not receiving data
        """
        # get the full list of rx with a corresponding tx that is in use,
        # then remove the ones that are receiving data.
        rxs = set()
        for lnk in self._active_links:
            if "vis-tx" in lnk[0]:
                rxs.add(lnk[0].replace("vis-tx", "vis-rx"))
        for lnk in self._active_links:
            if lnk[1] in rxs:
                rxs.remove(lnk[1])
        return rxs

    def _parse_link(self, link: str):
        """
        Each link is in the format of "tx_fqdn -> rx_fqdn". If the
        link is disabled, then the text ends with [x].

        :param link: a string describing a singular SLIM link.

        :return: the pair of HPS tx and rx device FQDNs that make up a link.
        :rtype: list[str]
        """
        cleaned_link = re.sub(r"[\s\t]", "", link)  # removes all whitespaces

        # ignore disabled links or lines without the expected format
        if cleaned_link.endswith("[x]") or ("->" not in cleaned_link):
            return None

        tx_rx_pair = cleaned_link.split("->")
        if len(tx_rx_pair) == 2:
            return tx_rx_pair
        return None

    def _validate_mesh_config(self, links: list) -> None:
        """
        Checks if the requested SLIM configuration is valid.

        :param links: a list of HPS tx and rx device pairs to be configured as SLIM links.
        :raise Tango exception: if SLIM configuration is not valid.
        """
        tx_set = set([x[0] for x in links])
        rx_set = set([y[1] for y in links])
        if len(tx_set) != len(rx_set) or len(tx_set) != len(links):
            msg = "Tx and Rx devices must be unique in the configuration."
            self.logger.error(msg)
            tango.Except.throw_exception(
                "Slim_Validate_",
                msg,
                "_validate_mesh_config()",
            )
        return

    def _parse_links_yaml(self, yaml_str: str) -> list[list[str]]:
        """
        Parse a yaml string containing the mesh links.

        :param yaml_str: the string defining the mesh links
        :raise Tango exception: if the configuration is not valid yaml.
        :return: a list of HPS tx and rx device pairs as [Tx FQDN, Rx FQDN]
        :rtype: list[list[str]]
        """
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            self.logger.error(f"Failed to load YAML: {e}")
            tango.Except.throw_exception(
                "Slim_Parse_YAML",
                "Cannot parse SLIM configuration YAML",
                "_parse_links_yaml()",
            )

        links = [
            self._parse_link(line)
            for value in data.values()
            for line in value
            if self._parse_link(line) is not None
        ]

        self._validate_mesh_config(
            links
        )  # throws exception if validation fails
        return links
