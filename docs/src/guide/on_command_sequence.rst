MCS On Command
==========================

The following diagram shows the ``CbfController`` On command sequence and how it integrates with other
components in the Mid.CBF system. The steps are outlined in detail in the 
`Engineering Console <https://developer.skatelescope.org/projects/ska-mid-cbf-engineering-console/en/latest/system.html#on-command-sequence>`_.

From a MCS perspective, the On command sequence consists of the following steps:

- Arrows 4-7: Power on the Talon-DX boards
- Arrow 9: Attempt to connect to each board over SSH (see :ref:`TalonDxComponentManager Class`)
- Arrows 8-9: Copy the relevant binaries and bitstreams to each board
- Arrow 10: Start up the HPS Master on each board
- Arrow 12: Send the ``configure`` to each HPS Master device server

.. figure:: ../diagrams/on-command-sequence.png
    :align: center
    
    MCS On Command Sequence