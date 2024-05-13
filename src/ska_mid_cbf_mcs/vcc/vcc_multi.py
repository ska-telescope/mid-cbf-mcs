"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""

from tango.server import run

from ska_mid_cbf_mcs.vcc.vcc_device import Vcc
from ska_mid_cbf_mcs.vcc.vcc_search_window import VccSearchWindow

__all__ = ["main"]


def main(args=None, **kwargs):
    return run(classes=(VccSearchWindow, Vcc), args=args, **kwargs)


if __name__ == "__main__":
    main()
