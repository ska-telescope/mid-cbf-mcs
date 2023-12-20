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

Command Sequence
-----------------

Off Sequence
++++++++++++++

The sequence diagram below shows the main sequence of calls in MCS
when the Off command is called. Return calls are not shown.

.. uml:: ../../diagrams/off-command-sequence.puml

InitSysParam Sequence
++++++++++++++++++++++

The sequence diagram below shows the main sequence of calls in MCS
to initialize the system parameters.

.. uml:: ../../diagrams/initsysparam-command.puml

Configure Scan Sequence
++++++++++++++++++++++++

The sequence diagram below shows the main sequence of calls in MCS 
to configure a correlation scan. Return calls are not shown.

.. uml:: ../../diagrams/configure-corr-scan-mcs.puml   

The sequence diagram below shows additional detail for configuration of 
the VCC for a correlation scan.

.. uml:: ../../diagrams/configure-scan-vcc.puml

The sequence diagram below shows details of calls to configure a FSP for a 
correlation scan.

.. uml:: ../../diagrams/configure-scan-hps-fsp.puml

Abort Sequence
+++++++++++++++

The sequence diagram below shows the main sequence of calls in MCS 
to Abort from a correlation scan. Return calls are not shown.

.. uml:: ../../diagrams/abort-command.puml

ObsReset Sequence
++++++++++++++++++

The sequence diagram below shows the main sequence of calls in MCS
to return to IDLE via the ObsReset command for a correlation scan.
Return calls are not shown.

.. uml:: ../../diagrams/obsreset-command.puml

Restart Sequence
++++++++++++++++++

The sequence diagram below shows the main sequence of calls in MCS
to return to EMPTY via the Restart command for a correlation scan.
Return calls are not shown.

.. uml:: ../../diagrams/restart-command.puml


Serial Lightweight Intercnnect Mesh (SLIM)
--------------------------------------------

Ref: `SLIM IP Block <https://gitlab.drao.nrc.ca/SKA/slim>`_

SLIM Configuration
++++++++++++++++++

.. figure:: /diagrams/4-receptor-correlator.png
    :align: center

    SLIM Interconnections for AA0.5 CBF

SLIM Configuration Sequence
+++++++++++++++++++++++++++
AA0.5 quantities shown.

.. uml:: /diagrams/slim-configuration-fs.puml

.. uml:: /diagrams/slim-configuration-vis.puml

SLIM FS Links Definition Example YAML File
+++++++++++++++++++++++++++++++++++++++++++
`[x]` indicates inactive link.
Part of the `MID CBF AA0.5 Talondx-Config MCS Data Model <https://confluence.skatelescope.org/display/SWSI/MID+CBF+AA0.5+Talondx-Config+MCS+Data+Model>`_

.. literalinclude:: fs_slim_config.yaml

SLIM Visibility Links Definition Example YAML File
++++++++++++++++++++++++++++++++++++++++++++++++++++
`[x]` indicates inactive link.
Part of the `MID CBF AA0.5 Talondx-Config MCS Data Model <https://confluence.skatelescope.org/display/SWSI/MID+CBF+AA0.5+Talondx-Config+MCS+Data+Model>`_

.. literalinclude:: vis_slim_config.yaml

SLIM Tx / Rx Device Servers (HPS)
++++++++++++++++++++++++++++++++++++++++++

Note: See `SLIM Tx/Rx Documentation <https://gitlab.drao.nrc.ca/digital-systems/software/applications/ds-slim-tx-rx/-/blob/main/doc>` for more details.

**SLIM Tx**

Ref: `tx_slim.tango.json <https://gitlab.drao.nrc.ca/digital-systems/software/applications/ds-slim-tx-rx/-/blob/main/reg/tx/definition/tx_slim.tango.json>`_

Commands:

- **clear_read_counters** -- Clear the tx read_counters attribute.
- **phy_reset** -- Toggle the phy reset bit.

Read/Write Attributes:

- **idle_ctrl_word** (ULong64) -- Runtime configuration of the user portion of the idle control word that will be transmitted. The receiving end should be configured to match. Max bit width is 56b.

Read-Only Attributes:

- **debug_counter_width** (ULong) [0..63] -- The width of the counters in this instance. Units of bits. The counters will wrap back to zero when they exceed 2^<counter_width>-1. If zero, then there are no counters.
- **debug_xcvr_rate** (ULong) [0..255] -- The approximate bit rate of the transceiver. This combined with the counter width can be used to determine the maximum polling period before the counters wrap. Units are 10e9 bits per second (Gbps). Zero means 'unknown'.
- **debug_sup_user_idle** (Boolean) -- True when the functionality of setting a user idle word is available.
- **link_occupancy** (Double) [0..1] -- The link occupancy as a percentage (0-1).
- **generated_idle_ctrl_word** (ULong64) -- The generated idle control word value (that is unique for each link).
- **read_counters** (ULong64[3]) -- Read the counters after latching and clearing them simultaneously. The counter values are returned as elements in an array. Values: [0]: word count. [1]: packet count. [2]: idle count.


**SLIM Rx**
Ref: `rx_slim.tango.json <https://gitlab.drao.nrc.ca/digital-systems/software/applications/ds-slim-tx-rx/-/blob/main/reg/rx/definition/rx_slim.tango.json>`_

Commands:

- **initialize_connection (DevBoolean)** -- Change the RX input source and perform the connection sequence. Throws an exception if the connection failed. This should be called whenever the input source to the RX changes (whenever it is taken out of loopback/put into loopback). Takes loopback_enable argument.
- **clear_read_counters** -- Clear the rx read_counters attribute.
- **phy_reset** -- Toggle the transmit PHY reset.

Read/Write Attributes:

- **idle_ctrl_word** (ULong64) -- The RX idle control word. Writing this will change the idle control word used for error comparison. Reading this register will return the last idle control word captured from the datastream.
- **debug_alignment_and_lock_status** [0..5] (DevBoolean) -- An alignment and lock status rollup attribute for debug. Indicated read only values will be ignored on attribute writes. Values: [0]: 66b block alignment lost. Read '1' = alignment lost. Write '1' to clear. [1]: 66b block aligned. Read '1' = aligned. Read only. [2]: Clock data recovery lock lost. Read '1' = CDR lock lost. Write '1' to clear. [3]: Clock data recovery locked. Read '1' = CDR locked. Read only.

Read-Only Attributes:

- **debug_counter_width** (ULong) [0..63] -- The width of the counters in this instance. Units of bits. The counters will wrap back to zero when they exceed 2^<counter_width>-1. If zero, then there are no counters.
- **debug_xcvr_rate** (ULong) [0..255] -- The approximate bit rate of the transceiver. This combined with the counter width can be used to determine the maximum polling period before the counters wrap. Units are 10e9 bits per second (Gbps). Zero means 'unknown'.
- **debug_sup_user_idle** (Boolean) -- True when the functionality of setting a user idle word is available.
- **bit_error_rate** (Double) -- The bit error rate in 66b-word-errors per second.
- **link_occupancy** (Double) [0..1] -- The link occupancy as a percentage (0-1).
- **read_counters** (ULong64[6]) -- Read the counters after latching and clearing them simultaneously. The counter values are returned as elements in an array. Values: [0]: word count. [1]: packet count. [2]: idle count. [3]: idle error count. [4]: block lost count. [5]: CDR lost count.


