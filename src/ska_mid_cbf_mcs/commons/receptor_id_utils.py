# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements utilities for managing DISH/receptor identifiers."""

# from __future__ import annotations  # allow forward references in type hints

__all__ = ["receptor_id_str_to_int", "receptor_id_int_to_str"]


def receptor_id_str_to_int(receptor_id: str) -> int:
    """
    Convert DISH/receptor ID mnemonic string to integer.

    :param receptor_id: the DISH/receptor ID mnemonic as a string

    :return: the DISH/receptor ID as a sequential integer (1 to 197)
    """
    receptor_prefix = receptor_id[:3]
    receptor_number = receptor_id[3:]
    if receptor_prefix != "SKA" and receptor_prefix != "MKT":
        raise ValueError(
            "Incorrect DISH type prefix. Prefix must be SKA or MKT."
        )
    if len(receptor_number) != 3:
        raise ValueError(
            "Incorrect DISH instance size. Dish instance must be a 3 digit number."
        )
    if receptor_prefix == "SKA":
        if int(receptor_number) not in range(1, 134):
            raise ValueError(
                "Incorrect DISH instance. Dish instance for SKA DISH type is 1 to 133 incl."
            )
        else:
            return int(receptor_number)
    if receptor_prefix == "MKT":
        if int(receptor_number) not in range(64):
            raise ValueError(
                "Incorrect DISH instance. Dish instance for MKT DISH type is 0 to 63 incl."
            )
        else:
            return int(receptor_number) + 134


def receptor_id_int_to_str(receptor_id: int) -> str:
    """
    Convert DISH/receptor ID integer to mnemonic string.

    :param receptor_id: the DISH/receptor ID as an integer

    :return: the DISH/receptor ID mnemonic as a string
    """
    if receptor_id not in range(1, 198):
        raise ValueError(
            "Incorrect receptor instance. ID should be in the range 1 to 197."
        )
    if receptor_id < 134:
        return "SKA" + f"{receptor_id:03}"
    else:
        return "MKT" + f"{receptor_id - 134:03}"
