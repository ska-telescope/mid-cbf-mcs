from __future__ import annotations

import re

import yaml


def parse_link(txt: str):
    """
    Each link is in the format of "tx_fqdn -> rx_fqdn". If the
    link is disabled, then the text ends with [x].
    """
    tmp = re.sub(r"[\s\t]", "", txt)  # removes all whitespaces

    # ignore disabled links or lines without the expected format
    if tmp.endswith("[x]") or ("->" not in tmp):
        return None
    txrx = tmp.split("->")
    if len(txrx) != 2:
        raise RuntimeError(f"Failed to parse {txt}")
    return txrx


def parse_links_yaml(yaml_str: str):
    """
    parse a yaml string containing the mesh links.

    :param yaml_str: the string defining the mesh links

    :return: a list of [Tx FQDN, Rx FQDN]
    """
    links = list()
    data = yaml.safe_load(yaml_str)
    for k, v in data.items():
        for line in v:
            txrx = parse_link(line)
            if txrx is not None:
                links.append(txrx)
    return links


# TODO: REMOVE
if __name__ == "__main__":
    with open("test.yaml") as f:
        yaml_str = f.read()
    links = parse_links_yaml(yaml_str)
    print(links)
