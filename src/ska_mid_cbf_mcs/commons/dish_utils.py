# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.


from __future__ import annotations

# --- Constants for Mid.CBF (197 DISH IDs) --- #

# SKA DISH ID range: SKA001 - SKA133
SKA_DISH_INSTANCE_MIN = 1
SKA_DISH_INSTANCE_MAX = 133

# MKT DISH ID range: MKT000 - MKT063
MKT_DISH_INSTANCE_MIN = 0
MKT_DISH_INSTANCE_MAX = 63

DISH_TYPE_STR_LEN = 3


class DISHUtils:
    """
    Utilities for translation of DISH/receptor identifiers.
    """

    def __init__(self: DISHUtils, mapping: dict[any]) -> None:
        """
        Initialize a new instance.

        :param mapping: dict mapping the DISH ID and VCC ID.
        """

        self.dish_id_to_vcc_id = {}
        self.vcc_id_to_dish_id = {}
        self.dish_id_to_k = {}

        dish_dict = mapping["dish_parameters"]
        for dish_id, dish_params in dish_dict.items():
            self.dish_id_to_vcc_id[dish_id] = dish_params["vcc"]
            self.vcc_id_to_dish_id[dish_params["vcc"]] = dish_id
            self.dish_id_to_k[dish_id] = dish_params["k"]

    def is_Valid_DISH_Id(self: DISHUtils, argin: str) -> tuple[bool, str]:
        """
        Checks the DISH id is in range of either SKA001-SKA133 or MKT000-MKT063.
        Spaces before, after, or in the middle of the ID (e.g. "SKA 001", " SKA001",
        "SKA001 ") are not valid.

        :return: the result(bool) and message(str) as a Tuple(result, msg)
        """

        fail_msg = (
            f"DISH ID {argin} is not valid. It must be SKA001-SKA133"
            " or MKT000-MKT063. Spaces before, after, or in the middle"
            " of the ID are not accepted."
        )
        if argin[:DISH_TYPE_STR_LEN] == "SKA":
            id = int(argin[DISH_TYPE_STR_LEN:])
            if id < SKA_DISH_INSTANCE_MIN or id > SKA_DISH_INSTANCE_MAX:
                return (False, fail_msg)
        elif argin[:DISH_TYPE_STR_LEN] == "MKT":
            id = int(argin[DISH_TYPE_STR_LEN:])
            if id < MKT_DISH_INSTANCE_MIN or id > MKT_DISH_INSTANCE_MAX:
                return (False, fail_msg)
        else:
            return (False, fail_msg)
        return (True, "DISH ID is valid")

    def are_Valid_DISH_Ids(
        self: DISHUtils, dish_ids: list[str]
    ) -> tuple[bool, str]:
        """
        Checks a list of DISH IDs are either
        SKA001-SKA133 or MKT000-MKT063. Spaces before, after, or in the
        middle of the ID (e.g. "SKA 001", " SKA001", "SKA001 ")
        are not valid. Returns when the first invalid DISH ID is
        found.

        :param argin: list of DISH IDs to check
        :return: the result(bool) and message(str) as a Tuple(result, msg)
        """

        for dish_id in dish_ids:
            result = self.is_Valid_DISH_Id(dish_id)
            if result[0]:
                continue
            else:
                msg = result[1]
                return (False, msg)
        return (True, "DISH IDs are valid.")
