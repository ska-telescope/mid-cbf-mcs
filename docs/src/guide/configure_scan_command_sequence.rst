Configure Scan Command Sequence
================================

TBD Add diagram for MCS-VCC and MCS-FSP Configure Scan

The sequence diagram below shows the calls to configure an FSP for a correlation scan. The
MCS Fsp Corr Subarray calls the HSP Fsp Corr Controller which in turn sets up the
configuration for all the lower level HSP device servers.

.. figure:: ../diagrams/configure-scan-hps-fsp.png
    :align: center