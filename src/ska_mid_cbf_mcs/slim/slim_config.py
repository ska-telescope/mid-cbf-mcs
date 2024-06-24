import re

import yaml
from tango.Except import throw_exception


class SlimConfig:
    def __init__(self, yaml_str):
        """
        Constructor

        :param yaml_str: the string defining the mesh links
        :raise Tango exception: if the configuration is not valid yaml.
        """
        self._active_links = self._parse_links_yaml(yaml_str)

    def active_links(self):
        """
        Returns the active links defined in the yaml file.

        :return: a list of HPS tx and rx device pairs as [Tx FQDN, Rx FQDN]
        :rtype: list[list[str]]
        """
        return self._active_links

    def _parse_link(self, link: str):
        """
        Each link is in the format of "tx_fqdn -> rx_fqdn". If the
        link is disabled, then the text ends with [x].

        :param link: a string describing a singular SLIM link.

        :return: the pair of HPS tx and rx device FQDNs that make up a link.
        :rtype: list[str]
        """
        tmp = re.sub(r"[\s\t]", "", link)  # removes all whitespaces

        # ignore disabled links or lines without the expected format
        if tmp.endswith("[x]") or ("->" not in tmp):
            return None
        txrx = tmp.split("->")
        if len(txrx) != 2:
            return None
        return txrx

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
            self._logger.error(msg)
            throw_exception(
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
        links = list()
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            self._logger.error(f"Failed to load YAML: {e}")
            throw_exception(
                "Slim_Parse_YAML",
                "Cannot parse SLIM configuration YAML",
                "_parse_links_yaml()",
            )
        for k, v in data.items():
            for line in v:
                txrx = self._parse_link(line)
                if txrx is not None:
                    links.append(txrx)
        self._validate_mesh_config(
            links
        )  # throws exception if validation fails
        return links
