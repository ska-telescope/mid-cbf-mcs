# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements utilities for managing DISH/receptor identifiers."""

from __future__ import annotations  # allow forward references in type hints

from typing import Dict

__all__ = [
    "receptor_id_str_to_int",
    "receptor_id_int_to_str",
    "receptor_id_dict",
]

# TODO: confirm ordering of SKA/MKT IDs
"""
for Mid.CBF (197 receptor IDs):
    MKT receptor ID range: 1 - 64
    SKA receptor ID range: 65 - 197

currently (8 receptor IDs):
    MKT receptor ID range: 1 - 8
"""

RECEPTOR_ID_MIN = 1
RECEPTOR_ID_MAX = 8

SKA_DISH_TYPE_STR = "SKA"
SKA_DISH_INSTANCE_MIN = 1
SKA_DISH_INSTANCE_MAX = 133
SKA_DISH_INSTANCE_OFFSET = 64

MKT_DISH_TYPE_STR = "MKT"
MKT_DISH_INSTANCE_MIN = 0
MKT_DISH_INSTANCE_MAX = 63
MKT_DISH_INSTANCE_OFFSET = 1

DISH_TYPE_STR_LEN = 3


def receptor_id_str_to_int(receptor_id: str) -> int:
    """
    Convert DISH/receptor ID mnemonic string to integer.

    :param receptor_id: the DISH/receptor ID mnemonic as a string

    :return: the DISH/receptor ID as a sequential integer (1 to 197)
    """
    receptor_prefix = receptor_id[:DISH_TYPE_STR_LEN]
    receptor_number = receptor_id[DISH_TYPE_STR_LEN:]

    if receptor_prefix != SKA_DISH_TYPE_STR and receptor_prefix != MKT_DISH_TYPE_STR:
        raise ValueError(
            f"Incorrect DISH type prefix. Prefix must be {SKA_DISH_TYPE_STR} or {MKT_DISH_TYPE_STR}."
        )

    if len(receptor_number) != DISH_TYPE_STR_LEN:
        raise ValueError(
            f"Incorrect DISH instance size. Dish instance must be a {DISH_TYPE_STR_LEN} digit number."
        )

    if receptor_prefix == MKT_DISH_TYPE_STR:
        if int(receptor_number) not in range(MKT_DISH_INSTANCE_MIN, MKT_DISH_INSTANCE_MAX + 1):
            raise ValueError(
                f"Incorrect DISH instance. Dish instance for {MKT_DISH_TYPE_STR} DISH type is {MKT_DISH_INSTANCE_MIN} to {MKT_DISH_INSTANCE_MAX} incl."
            )
        else:
            return int(receptor_number) + MKT_DISH_INSTANCE_OFFSET

    if receptor_prefix == SKA_DISH_TYPE_STR:
        if int(receptor_number) not in range(SKA_DISH_INSTANCE_MIN, SKA_DISH_INSTANCE_MAX + 1):
            raise ValueError(
                f"Incorrect DISH instance. Dish instance for {SKA_DISH_TYPE_STR} DISH type is {SKA_DISH_INSTANCE_MIN} to {SKA_DISH_INSTANCE_MAX} incl."
            )
        else:
            return int(receptor_number) + SKA_DISH_INSTANCE_OFFSET


def receptor_id_int_to_str(receptor_id: int) -> str:
    """
    Convert DISH/receptor ID integer to mnemonic string.

    :param receptor_id: the DISH/receptor ID as an integer

    :return: the DISH/receptor ID mnemonic as a string
    """
    if receptor_id not in range(RECEPTOR_ID_MIN, RECEPTOR_ID_MAX + 1):
        raise ValueError(
            f"Incorrect receptor instance. ID should be in the range {RECEPTOR_ID_MIN} to {RECEPTOR_ID_MAX}."
        )

    if receptor_id in range(MKT_DISH_INSTANCE_MIN + MKT_DISH_INSTANCE_OFFSET, MKT_DISH_INSTANCE_MAX + 1):
        return MKT_DISH_TYPE_STR + str(receptor_id - MKT_DISH_INSTANCE_OFFSET).zfill(DISH_TYPE_STR_LEN)

    if receptor_id in range(SKA_DISH_INSTANCE_MIN + SKA_DISH_INSTANCE_OFFSET, SKA_DISH_INSTANCE_MAX + 1):
        return SKA_DISH_TYPE_STR + str(receptor_id - SKA_DISH_INSTANCE_OFFSET).zfill(DISH_TYPE_STR_LEN)


def receptor_id_dict() -> Dict[str, int]:
    """
    Output DISH ID string mnemonic to int in a dictionary.

    :return: the DISH/receptor ID translation as a dictionary
    """
    return {
        receptor_id_int_to_str(receptor): receptor
        for receptor in range(RECEPTOR_ID_MIN, RECEPTOR_ID_MAX)
    }
