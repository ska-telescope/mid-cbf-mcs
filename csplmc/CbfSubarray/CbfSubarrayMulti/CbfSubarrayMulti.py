from PyTango.server import run
import os
import sys

file_path = os.path.dirname(os.path.abspath(__file__))
pkg_path = os.path.abspath(os.path.join(file_path, "../"))
sys.path.insert(0, pkg_path)

from CbfSubarray.CbfSubarray import CbfSubarray
from SearchWindow.SearchWindow import SearchWindow

def main(args=None, **kwargs):
    return run(classes=(SearchWindow, CbfSubarray), args=args, **kwargs)


if __name__ == '__main__':
    main()
