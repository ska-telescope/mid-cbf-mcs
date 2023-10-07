# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements utilities for managing DISH/receptor identifiers."""

from __future__ import annotations  # allow forward references in type hints

import re
from typing import List, Tuple


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

    def __init__(self: ReceptorUtils, mapping) -> None:
        """
        Initialize a new instance.

        :param mapping: dict mapping the receptor ID and VCC ID.
        """
        result = self.is_valid_dish_vcc_mapping(mapping)
        if not result[0]:
            raise ValueError(result[1])

        self.receptor_id_to_vcc_id = {}
        self.vcc_id_to_receptor_id = {}
        self.receptor_id_to_k = {}
        self.receptor_id_to_int = {}

        dish_dict = mapping["dish_parameters"]
        for r, v in dish_dict.items():
            self.receptor_id_to_vcc_id[r] = v["vcc"]
            self.vcc_id_to_receptor_id[v["vcc"]] = r
            self.receptor_id_to_k[r] = v["k"]
            self.receptor_id_to_int[r] = self._receptor_id_str_to_int(r)

    def _receptor_id_str_to_int(self: ReceptorUtils, receptor_id: str) -> int:
        """
        Convert DISH/receptor ID mnemonic string to integer.

        :param receptor_id: the DISH/receptor ID mnemonic as a string

        :return: the DISH/receptor ID as a sequential integer (1 to 197)
        """
        receptor_prefix = receptor_id[: self.DISH_TYPE_STR_LEN]
        receptor_number = receptor_id[self.DISH_TYPE_STR_LEN :]

        if receptor_prefix == self.MKT_DISH_TYPE_STR:
            return int(receptor_number) + self.MKT_DISH_INSTANCE_OFFSET
        elif receptor_prefix == self.SKA_DISH_TYPE_STR:
            return int(receptor_number) + self.SKA_DISH_INSTANCE_OFFSET
        else:
            raise ValueError(
                f"Incorrect DISH type prefix. Prefix must be {self.SKA_DISH_TYPE_STR} or {self.MKT_DISH_TYPE_STR}."
            )

    @staticmethod
    def is_valid_dish_vcc_mapping(mapping) -> Tuple[bool, str]:
        """
        Checks if the dish vcc mapping is valid. The checks include:
        - dish IDs are valid and unique
        - vcc IDs are valid and unique
        - k values are integers in range of 1-2222

        :return: the result(bool) and message(str) as a Tuple(result, msg)
        """
        dish_dict = mapping["dish_parameters"]
        dish_id_set = set()
        vcc_id_set = set()
        for dish_id, v in dish_dict.items():
            # Dish ID must be SKA001-133, MKT000-063
            if dish_id[0 : ReceptorUtils.DISH_TYPE_STR_LEN] == "SKA":
                id = int(dish_id[ReceptorUtils.DISH_TYPE_STR_LEN :])
                if (
                    id < ReceptorUtils.SKA_DISH_INSTANCE_MIN
                    or id > ReceptorUtils.SKA_DISH_INSTANCE_MAX
                ):
                    return (False, "Invalid Dish ID")
            elif dish_id[0 : ReceptorUtils.DISH_TYPE_STR_LEN] == "MKT":
                id = int(dish_id[ReceptorUtils.DISH_TYPE_STR_LEN :])
                if (
                    id < ReceptorUtils.MKT_DISH_INSTANCE_MIN
                    or id > ReceptorUtils.MKT_DISH_INSTANCE_MAX
                ):
                    return (False, "Invalid Dish ID")
            else:
                return (False, "Invalid Dish ID")

            # Dish ID must be unique
            if dish_id not in dish_id_set:
                dish_id_set.add(dish_id)
            else:
                return (False, f"Duplicated Dish ID {dish_id}")

            # VCC ID must be an integer in 1 - 197 (TODO: confirm)
            if v["vcc"] < 1 or v["vcc"] > 197:
                return (False, f"Invalid VCC ID {v['vcc']}")

            # VCC ID must be unique
            if v["vcc"] not in vcc_id_set:
                vcc_id_set.add(v["vcc"])
            else:
                return (False, f"Duplicated VCC ID {v['vcc']}")

            # k values must be an integer in 1 - 2222
            if v["k"] < 1 or v["k"] > 2222:
                return (False, f"Invalid k value {v['k']}")
        return (True, "")

    @staticmethod
    def are_Valid_Receptor_Ids(argin: List[str]) -> Tuple[bool, str]:
        """
        Checks a list of receptor ids are either
        SKA001-SKA133 or MKT000-MKT063. Spaces before, after, or in the
        middle of the ID (e.g. "SKA 001", " SKA001", "SKA001 ")
        are not valid. Returns when the first invalid receptor ID is
        found.

        :return: the result(bool) and message(str) as a Tuple(result, msg)
        """

        for i in argin:
            result = ReceptorUtils.is_Valid_Receptor_Id(i)
            if result[0]:
                continue
            else:
                # receptor ID is not a valid ID, return immediately
                msg = result[1]
                return (False, msg)
        # All the receptor IDs are valid.
        return (True, "Receptor IDs are valid.")

    @staticmethod
    def is_Valid_Receptor_Id(argin: str) -> Tuple[bool, str]:
        """
        Checks the receptor id is either
        SKA001-SKA133 or MKT000-MKT063. Spaces before, after, or in the
        middle of the ID (e.g. "SKA 001", " SKA001", "SKA001 ")
        are not valid.

        :return: the result(bool) and message(str) as a Tuple(result, msg)
        """
        # The receptor ID must be in the range of SKA[001-133] or MKT[000-063]
        pattern = "^(SKA(00[1-9]|0[1-9][0-9]|1[0-2][0-9]|13[0-3]))$|^(MKT(0[0-5][0-9]|06[0-3]))$"
        if re.match(pattern, argin):
            msg = "Receptor ID is valid"
            return (True, msg)
        else:
            # receptor ID is not a valid ID
            msg = (
                f"Receptor ID {argin} is not valid. It must be SKA001-SKA133"
                " or MKT000-MKT063. Spaces before, after, or in the middle"
                " of the ID are not accepted."
            )
            return (False, msg)
