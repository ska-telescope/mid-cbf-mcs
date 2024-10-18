# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF MCS project
#
#
#
"""Release information for SKA Mid.CBF MCS Python Package."""
import sys
from typing import Optional

name = "ska_mid_cbf_mcs"
version = "1.1.0-rc.1"
version_info = version.split(".")
description = "A set of Mid MCS tango devices for the SKA Telescope."
author = "Team CIPA"
author_email = "taylor.huang@mda.space"
url = "https://gitlab.com/ska-telescope/ska-mid-cbf-mcs"
license = "BSD-3-Clause"  # noqa: A001
copyright = ""  # noqa: A001


def get_release_info(clsname: Optional[str] = None) -> str:
    """
    Return a formatted release info string.

    :param clsname: optional name of class to add to the info
    :type clsname: str

    :return: str
    """
    rmod = sys.modules[__name__]
    info = ", ".join(
        # type: ignore[attr-defined]
        (rmod.name, rmod.version, rmod.description)
    )
    if clsname is None:
        return info
    return ", ".join((clsname, info))


if __name__ == "__main__":
    print(version)
