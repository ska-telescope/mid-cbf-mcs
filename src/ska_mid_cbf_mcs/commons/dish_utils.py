# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

"""This module implements utilities for managing DISH identifiers."""

from __future__ import annotations  # allow forward references in type hints

from typing import List, Tuple


class DISHUtils:
    """
    Utilities for translation of DISH/receptor identifiers.

    for Mid.CBF (197 DISH IDs):
        MKT DISH ID range: 1 - 64
        SKA DISH ID range: 65 - 197
    """

    SKA_DISH_TYPE_STR = "SKA"
    SKA_DISH_INSTANCE_MIN = 1
    SKA_DISH_INSTANCE_MAX = 133
    SKA_DISH_INSTANCE_OFFSET = 0

    MKT_DISH_TYPE_STR = "MKT"
    MKT_DISH_INSTANCE_MIN = 0
    MKT_DISH_INSTANCE_MAX = 63
    MKT_DISH_INSTANCE_OFFSET = 134

    DISH_TYPE_STR_LEN = 3

    def __init__(self: DISHUtils, mapping) -> None:
        """
        Initialize a new instance.

        :param mapping: dict mapping the DISH ID and VCC ID.
        """

        self.dish_id_to_vcc_id = {}
        self.vcc_id_to_dish_id = {}
        self.dish_id_to_k = {}
        self.dish_id_to_int = {}

        dish_dict = mapping["dish_parameters"]
        for r, v in dish_dict.items():
            self.dish_id_to_vcc_id[r] = v["vcc"]
            self.vcc_id_to_dish_id[v["vcc"]] = r
            self.dish_id_to_k[r] = v["k"]
            self.dish_id_to_int[r] = self._dish_id_str_to_int(r)

    def _dish_id_str_to_int(self: DISHUtils, dish_id: str) -> int:
        """
        Convert DISH/receptor ID mnemonic string to integer.

        :param dish_id: the DISH/receptor ID mnemonic as a string

        :return: the DISH/receptor ID as a sequential integer (1 to 197)
        """
        prefix = dish_id[: self.DISH_TYPE_STR_LEN]
        number = dish_id[self.DISH_TYPE_STR_LEN :]

        if prefix == self.MKT_DISH_TYPE_STR:
            return int(number) + self.MKT_DISH_INSTANCE_OFFSET
        elif prefix == self.SKA_DISH_TYPE_STR:
            return int(number) + self.SKA_DISH_INSTANCE_OFFSET
        else:
            raise ValueError(
                f"Incorrect DISH type prefix. Prefix must be {self.SKA_DISH_TYPE_STR} or {self.MKT_DISH_TYPE_STR}."
            )

    @staticmethod
    def are_Valid_DISH_Ids(argin: List[str]) -> Tuple[bool, str]:
        """
        Checks a list of DISH IDs are either
        SKA001-SKA133 or MKT000-MKT063. Spaces before, after, or in the
        middle of the ID (e.g. "SKA 001", " SKA001", "SKA001 ")
        are not valid. Returns when the first invalid DISH ID is
        found.

        :return: the result(bool) and message(str) as a Tuple(result, msg)
        """

        for i in argin:
            result = DISHUtils.is_Valid_DISH_Id(i)
            if result[0]:
                continue
            else:
                # DISH ID is not a valid ID, return immediately
                msg = result[1]
                return (False, msg)
        # All the DISH IDs are valid.
        return (True, "DISH IDs are valid.")

    @staticmethod
    def is_Valid_DISH_Id(argin: str) -> Tuple[bool, str]:
        """
        Checks the DISH id is either
        SKA001-SKA133 or MKT000-MKT063. Spaces before, after, or in the
        middle of the ID (e.g. "SKA 001", " SKA001", "SKA001 ")
        are not valid.

        :return: the result(bool) and message(str) as a Tuple(result, msg)
        """
        # The DISH ID must be in the range of SKA[001-133] or MKT[000-063]
        fail_msg = (
            f"DISH ID {argin} is not valid. It must be SKA001-SKA133"
            " or MKT000-MKT063. Spaces before, after, or in the middle"
            " of the ID are not accepted."
        )
        if argin[0 : DISHUtils.DISH_TYPE_STR_LEN] == "SKA":
            id = int(argin[DISHUtils.DISH_TYPE_STR_LEN :])
            if (
                id < DISHUtils.SKA_DISH_INSTANCE_MIN
                or id > DISHUtils.SKA_DISH_INSTANCE_MAX
            ):
                return (False, fail_msg)
        elif argin[0 : DISHUtils.DISH_TYPE_STR_LEN] == "MKT":
            id = int(argin[DISHUtils.DISH_TYPE_STR_LEN :])
            if (
                id < DISHUtils.MKT_DISH_INSTANCE_MIN
                or id > DISHUtils.MKT_DISH_INSTANCE_MAX
            ):
                return (False, fail_msg)
        else:
            return (False, fail_msg)
        return (True, "DISH ID is valid")
