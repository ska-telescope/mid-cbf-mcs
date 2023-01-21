delaymodel.json

In order to accommodate a range of tests (with various combinations of 
receptors belonging a subarray), the input delay models test file 
delaymodel.json was created so that it contains DMs for ALL 4 receptors.

Prior to a given test, the DMs corresponding to the receptors 
that do NOT belong to the subarray under test, are removed.

This files contains 3 instances of the delay model object to 
be obtained for the TMC emulator, used for the purpose of 
simulating 3 periodic updates (events).