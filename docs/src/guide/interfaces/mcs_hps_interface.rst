MCS to HPS
=====================
The interface from the MCS to the HPS is largely in the form of communication between
Tango devices running on either side. 

The interface also currently consists of low-level SSH calls from the MCS to the Talon-DX
boards, which are used to copy FPGA bitstreams and Tango device server binaries to the boards
and start the HPS Master process. This functionality may be moved in the future, but for now
it is implemented in the :ref:`TalonDxComponentManager Class`, which is instantiated by the
:ref:`CbfController`.

MCS and HPS Master DS
----------------------
The interface between the MCS and the HPS Master device server is primarily made up
of the ``configure`` command sent from the MCS to the HPS master, which programs the
FPGA and spawns the remaining HPS device servers. Before this command can be run, it is 
expected that the MCS has already copied the necessary bitstreams and binaries to the board
and the HPS master has obviously been started. This is all handled automatically as part of
the :ref:`MCS On Command`.

The ``configure`` command has one argument, which is a JSON-formatted string. An example
of its contents can be seen below.

.. code-block:: json

    {
        "description": "Configures Talon DX to run VCC firmware and devices.",
        "target": "talon1",
        "ip_address": "169.254.100.1",
        "ds_hps_master_fqdn": "talondx-001/hpsmaster/hps-1",
        "fpga_path": "/lib/firmware",
        "fpga_dtb_name": "vcc3_2ch4.dtb",
        "fpga_rbf_name": "vcc3_2ch4.core.rbf",
        "fpga_label": "base",
        "ds_path": "/lib/firmware/hps_software/vcc_test",
        "server_instance": "talon1_test",
        "devices": [
            "dscircuitswitch",
            "dsdct",
            "dsfinechannelizer",
            "dstalondxrdma",
            "dsvcc"
        ]
    }

MCS On Command
----------------

The following diagram shows the ``CbfController`` On command sequence and how it integrates with other
components in the Mid.CBF system. The steps are outlined in detail in the 
`Engineering Console <https://developer.skatelescope.org/projects/ska-mid-cbf-engineering-console/en/latest/system.html#on-command-sequence>`_.

From a MCS perspective, the On command sequence consists of the following steps:

- Arrows 4-7: Power on the Talon-DX boards
- Arrow 9: Attempt to connect to each board over SSH (see :ref:`TalonDxComponentManager Class`)
- Arrows 8-9: Copy the relevant binaries and bitstreams to each board
- Arrow 10: Start up the HPS Master on each board
- Arrow 12: Send the ``configure`` to each HPS Master device server

.. figure:: ../../diagrams/on-command-sequence.png
    :align: center
    
    MCS On Command Sequence

Configure Scan Command Sequence
--------------------------------

The sequence diagram below shows the main sequence of calls in MCS 
to configure a correlation scan. Return calls are not shown.

.. uml:: ../../diagrams/configure-corr-scan-mcs.puml   

The sequence diagram below shows additional detail for configuration of 
the VCC for a correlation scan.

.. uml:: ../../diagrams/configure-scan-vcc.puml

The sequence diagram below shows details of calls to configure a FSP for a 
correlation scan.

.. uml:: ../../diagrams/configure-scan-hps-fsp.puml

Abort/ObsReset/Restart Command Sequence
----------------------------------------

The sequence diagram below shows the main sequence of calls in MCS 
to Abort from a correlation scan, and return to either IDLE or EMPTY via the 
ObsReset and Restart commands, respectively. Return calls are not shown.

.. uml:: ../../diagrams/abort-command.puml

.. uml:: ../../diagrams/obsreset-command.puml
    
.. uml:: ../../diagrams/restart-command.puml
