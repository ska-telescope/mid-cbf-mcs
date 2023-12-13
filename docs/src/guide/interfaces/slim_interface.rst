Serial Lightweight Intercnnect Mesh (SLIM)
=================================================

Ref: `SLIM IP Block <https://gitlab.drao.nrc.ca/SKA/slim>`_

SLIM Configuration
-------------------

.. figure:: /diagrams/VCC-SLIM-FSP.png
    :align: center

    VCC-SLIM-FSP Context

SLIM Configuration Sequence
***************************
AA0.5 quantities shown.

.. uml:: /diagrams/slim-configuration-fs.puml

.. uml:: /diagrams/slim-configuration-vis.puml

SLIM FS Links Definition YAML File
**********************************
`[x]` indicates inactive link.
Part of the `MID CBF AA0.5 Talondx-Config MCS Data Model <https://confluence.skatelescope.org/display/SWSI/MID+CBF+AA0.5+Talondx-Config+MCS+Data+Model>`_

.. literalinclude:: fs_slim_config.yaml

SLIM Visibility Links Definition YAML File
******************************************
`[x]` indicates inactive link.
Part of the `MID CBF AA0.5 Talondx-Config MCS Data Model <https://confluence.skatelescope.org/display/SWSI/MID+CBF+AA0.5+Talondx-Config+MCS+Data+Model>`_

.. literalinclude:: vis_slim_config.yaml

SLIM Tx / Rx Device Servers (Current HPS)
*****************************************

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

