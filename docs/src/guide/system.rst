Overview
********
The Mid.CBF Master Control Software (MCS) runs on a COTS server to provide a 
high-level interface to TMC and CSP.LMC, and translate the high-level commands 
into the configuration and control of individual Talon-DX boards.

System Context
==============
The following diagram shows the Mid.CBF MCS as it fits into the rest of the CSP Mid
system.

.. figure:: ../diagrams/mcs-context.png
    :align: center

    MCS System Context

Interfaces
==========

LMC to MCS Interface
--------------------
See the `ICD document <https://drive.google.com/drive/folders/1CQJAJP1RhRuSvaM1OQhnxBZZ4xH1Pq_m>`_ for details of this interface.

MCS to TDC Interface
--------------------
The interface from the MCS to the TDC is largely in the form of communication between
Tango devices running on either side. Currently only one such Tango device is running
on each Talon-DX board that the MCS directly communicates with; this is known as the 
HPS Master.

The interface also currently consists of low-level SSH calls from the MCS to the Talon-DX
boards, which are used to copy FPGA bitstreams and Tango device server binaries to the boards
and start the HPS Master process. This functionality may be moved in the future, but for now
it is implemented in the :ref:`TalonDxComponentManager Class`, which is instantiated by the
:ref:`CbfController`.

MCS and HPS Master DS
^^^^^^^^^^^^^^^^^^^^^
The interface between the MCS and the HPS Master device server is primarily made up
of the ``configure`` command sent from the MCS to the HPS master, which programs the
FPGA and spawns the remaining HPS device servers. Before this command can be run, it is 
expected that the MCS has already copied the necessary bitstreams and binaries to the board
and the HPS master has obviously been started. This is all handled automatically as part of
the :ref:`On Command Sequence`.

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

On Command Sequence
===================
The following diagram shows the ``CbfController`` On command sequence and how it integrates with other
components in the Mid.CBF system. The steps are outlined in detail in the 
`Engineering Console <https://developer.skatelescope.org/projects/ska-mid-cbf-engineering-console/en/latest/system.html#on-command-sequence>`_.

From a MCS perspective, the On command sequence consists of the following steps:

- Arrows 4-7: Power on the Talon-DX boards (see :ref:`TalonLRU Device` and :ref:`PowerSwitch Device`)
- Arrow 9: Attempt to connect to each board over SSH (see :ref:`TalonDxComponentManager Class`)
- Arrows 8-9: Copy the relevant binaries and bitstreams to each board
- Arrow 10: Start up the HPS Master on each board
- Arrow 12: Send the ``configure`` to each HPS Master device server

.. figure:: ../diagrams/on-command-sequence.png
    :align: center
    
    MCS On Command Sequence
