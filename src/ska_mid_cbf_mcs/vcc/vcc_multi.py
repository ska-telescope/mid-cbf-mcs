"""
Author: James Jiang James.Jiang@nrc-cnrc.gc.ca,
Herzberg Astronomy and Astrophysics, National Research Council of Canada
Copyright (c) 2019 National Research Council of Canada
"""


from tango.server import run

from ska_mid_cbf_mcs.vcc.vcc_device import Vcc

__all__ = ["main"]


def main(args=None, **kwargs):
    # TODO: CIP-1470 removed VCC search window
    return run(classes=(Vcc), args=args, **kwargs)


if __name__ == "__main__":
    main()
