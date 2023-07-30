# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements utilities for managing DISH/receptor identifiers."""

from __future__ import annotations  # allow forward references in type hints

import json
from typing import Dict

RECEPTOR_ID_DICT_PATH = "mnt/receptor_id_dict/"


class ReceptorUtils:
    """
    Utilities for translation of DISH/receptor identifiers.

    for Mid.CBF (197 receptor IDs):
        MKT receptor ID range: 1 - 64
        SKA receptor ID range: 65 - 197

    currently (8 receptor IDs):
        MKT receptor ID range: 1 - 8
    """

    RECEPTOR_ID_MIN = 1
    RECEPTOR_ID_MAX = 197

    SKA_DISH_TYPE_STR = "SKA"
    SKA_DISH_INSTANCE_MIN = 1
    SKA_DISH_INSTANCE_MAX = 133
    SKA_DISH_INSTANCE_OFFSET = 0

    MKT_DISH_TYPE_STR = "MKT"
    MKT_DISH_INSTANCE_MIN = 0
    MKT_DISH_INSTANCE_MAX = 63
    MKT_DISH_INSTANCE_OFFSET = 134

    DISH_TYPE_STR_LEN = 3

    @property
    def receptors(self: ReceptorUtils) -> Dict[str, int]:
        """Return the receptor ID str to int translation dictionary."""
        return self._receptor_id_dict

    def __init__(self: ReceptorUtils, num_vcc: int) -> None:
        """
        Initialize a new instance.

        :param num_vcc: number of VCCs in the system
        """
        # load the receptor ID dictionary from specified JSON file
        receptor_id_dict_file_name = (
            f"{RECEPTOR_ID_DICT_PATH}receptor_id_dict_{num_vcc}r.json"
        )

        with open(receptor_id_dict_file_name, "r") as f:
            self._receptor_id_dict = json.loads(f.read())

        if len(self._receptor_id_dict) != num_vcc:
            raise ValueError(
                f"Incorrect number ({len(self._receptor_id_dict)}) of receptors specified in file {receptor_id_dict_file_name} ; {num_vcc} VCCs currently available."
            )
        #for receptor_id_str, receptor_id_int in self._receptor_id_dict.items():
        #    if receptor_id_int != self.receptor_id_str_to_int(receptor_id_str):
        #        raise ValueError(
        #            f"Encountered an incorrect entry for DISH ID {receptor_id_str}: {receptor_id_int} (should be {self.receptor_id_str_to_int(receptor_id_str)})"
        #        )

    def receptor_id_str_to_int(self: ReceptorUtils, receptor_id: str) -> int:
        """
        Convert DISH/receptor ID mnemonic string to integer.

        :param receptor_id: the DISH/receptor ID mnemonic as a string

        :return: the DISH/receptor ID as a sequential integer (1 to 197)
        """
        receptor_prefix = receptor_id[: self.DISH_TYPE_STR_LEN]
        receptor_number = receptor_id[self.DISH_TYPE_STR_LEN :]

        if (
            receptor_prefix != self.SKA_DISH_TYPE_STR
            and receptor_prefix != self.MKT_DISH_TYPE_STR
        ):
            raise ValueError(
                f"Incorrect DISH type prefix. Prefix must be {self.SKA_DISH_TYPE_STR} or {self.MKT_DISH_TYPE_STR}."
            )

        if len(receptor_number) != self.DISH_TYPE_STR_LEN:
            raise ValueError(
                f"Incorrect DISH instance size. Dish instance must be a {self.DISH_TYPE_STR_LEN} digit number."
            )

        if receptor_prefix == self.MKT_DISH_TYPE_STR:
            if int(receptor_number) not in range(
                self.MKT_DISH_INSTANCE_MIN, self.MKT_DISH_INSTANCE_MAX + 1
            ):
                raise ValueError(
                    f"Incorrect DISH instance. Dish instance for {self.MKT_DISH_TYPE_STR} DISH type is {self.MKT_DISH_INSTANCE_MIN} to {self.MKT_DISH_INSTANCE_MAX} incl."
                )
            else:
                return int(receptor_number) + self.MKT_DISH_INSTANCE_OFFSET

        if receptor_prefix == self.SKA_DISH_TYPE_STR:
            if int(receptor_number) not in range(
                self.SKA_DISH_INSTANCE_MIN, self.SKA_DISH_INSTANCE_MAX + 1
            ):
                raise ValueError(
                    f"Incorrect DISH instance. Dish instance for {self.SKA_DISH_TYPE_STR} DISH type is {self.SKA_DISH_INSTANCE_MIN} to {self.SKA_DISH_INSTANCE_MAX} incl."
                )
            else:
                return int(receptor_number) + self.SKA_DISH_INSTANCE_OFFSET

    def receptor_id_int_to_str(self: ReceptorUtils, receptor_id: int) -> str:
        """
        Convert DISH/receptor ID integer to mnemonic string.

        :param receptor_id: the DISH/receptor ID as an integer

        :return: the DISH/receptor ID mnemonic as a string
        """
        if receptor_id not in range(
            self.RECEPTOR_ID_MIN, self.RECEPTOR_ID_MAX + 1
        ):
            raise ValueError(
                f"Incorrect receptor instance. ID should be in the range {self.RECEPTOR_ID_MIN} to {self.RECEPTOR_ID_MAX}."
            )

        if receptor_id in range(
            self.MKT_DISH_INSTANCE_MIN + self.MKT_DISH_INSTANCE_OFFSET,
            self.MKT_DISH_INSTANCE_MAX + self.MKT_DISH_INSTANCE_OFFSET + 1,
        ):
            return self.MKT_DISH_TYPE_STR + str(
                receptor_id - self.MKT_DISH_INSTANCE_OFFSET
            ).zfill(self.DISH_TYPE_STR_LEN)

        if receptor_id in range(
            self.SKA_DISH_INSTANCE_MIN + self.SKA_DISH_INSTANCE_OFFSET,
            self.SKA_DISH_INSTANCE_MAX + self.SKA_DISH_INSTANCE_OFFSET + 1,
        ):
            return self.SKA_DISH_TYPE_STR + str(
                receptor_id - self.SKA_DISH_INSTANCE_OFFSET
            ).zfill(self.DISH_TYPE_STR_LEN)

    def receptor_id_dict(self: ReceptorUtils) -> Dict[str, int]:
        """
        Output DISH ID string mnemonic to int in a dictionary.

        :return: the DISH/receptor ID translation as a dictionary
        """
        return {
            self.receptor_id_int_to_str(receptor): receptor
            for receptor in range(
                self.RECEPTOR_ID_MIN, self.RECEPTOR_ID_MAX + 1
            )
        }
