# Test Parameters

## Summary

This folder contains prototype JSON definitions, JSON schemas, and code snippets to help understand parameterized testing of [Mid CBF AA0.5 Use Cases](https://confluence.skatelescope.org/display/SE/Mid+CBF+AA0.5+Use+Cases). The test parameters are focused on the [MID CBF Signal Chain Verification](https://confluence.skatelescope.org/display/SE/Mid+CBF+AA0.5+Use+Cases#MidCBFAA0.5UseCases-MidCBFSignalChainVerification) use case and corresponding test [XTP-25202](https://jira.skatelescope.org/browse/XTP-25202).

See `tests.json` for example test parameters. Each test is given by a test id and defines a set of test parameters, including: input test data, delay model package, subarray configuration, scan configuration, and test checkpoints.

To generate the `test_parameters.json` file and/or generate the `signal_chain_verification.feature` file for the MID CBF Signal Chain Verification Test, follow these steps:
1. Create a Python virtual environment and install the dependencies (if you already have a virtual environment created, skip the first three lines):

```
cd ~ # To navigate to your home directory on the dev server
pip install virtualenv
python3 -m virtualenv venv
source ~/venv/bin/activate
pip install -r requirements.txt
```
2. Clone this repo and run `cd <path/to/ska-mid-cbf-system-tests/test_parameters>`
3. Run `./test_parameters.py` with at least one of the following flags: `-t` to generate the `test_parameters.json` file, and/or `-f` to generate the `signal_chain_verification.feature` file.

## BITE Configuration Parameters
See the `bite_config_parameters` folder.

### BITE Config
See examples in `bite_configs.json`.
Each Test ID in `tests.json` is assigned to one particular set of CBF Input Data defined in `cbf_input_data.json`. Each of these sets of CBF Input Data (i.e. "talon3 basic gaussian noise", "talons 1-4 basic gaussian noise", etc.) is assigned a BITE Configuration ID for each of its "receptors", which corresponds to one of the BITE Configuration IDs defined in `bite_configs.json`. Each of these configurations (i.e. "basic gaussian noise", "ramp filtered gaussian noise and tone", etc) contains a set of parameters to be used in configuring the BITE, which the BITE Client will write to the relevant device servers via Tango. In a given bite configuration, both polarizations of each gaussian noise source are assigned one of the filter types defined in `filters.json`, whose exact parameters will be parsed by the BITE Client.
Each BITE configuration in `bite_configs.json` has a "description", an array of "sources" (of Gaussian noise), and array of "tone_gens".
The "sources" array can be 4 elements long. Each element in the array must be given:
* a description of the source
* a "pol_coupling_rho", or polarization coupler correlation coefficient, which must be provided in the range of [-1.0, 1.0]. This rho value will be scaled by a factor of 2^16 and written directly to the polarization_coupler as the linear scaling coefficient of the cross-connected path ("alpha"); and it will be used in calculating the linear scaling coefficient of the straight-through path ("beta") which will also be scaled by a factor of 2^16 and written to the polarization_coupler. 
* a value of 'true' or 'false' for the pol_Y_1_sample_delay, which will (respectively) enable or disable the delay element in the cross-connected path of the polarization coupler 

Additionally, each element in the "sources" array must have a "gaussian" object whose two polarization properties ("pol_x" and "pol_y") are each given 
* a randomization seed for Gaussian noise generation, which must be an integer in the range of 0 to 65445
* a "filter", which must match one of the filter names defined in filters.json, and will be applied to that noise component
* if desired, the "noise_mean" and "noise_std", or the mean and standard deviation of the Gaussian noise to be generated. The mean can be defined as any value between -32768 and 32767, and the standard deviation can be defined as any value between 0 and 65535. These are the values that will be written directly to the 16-bit registers.

Each BITE configuration can define an array of "tone_gens", or specifications for the LSTV Tone Generator device servers required for that configuration. This array can be left empty, in which case no tone(s) will be generated; or it can have a maximum of 4 elements. Each element in the array is split into two components, for polarizations X and Y, and each of these is defined with the frequency and magnitude (or "scale", as this parameter is named in `bite_configs.json`) of the sinusoidal signal to be generated. These are then converted into values that can be written to the registers of the "bite_tone_gen" IP block: the magnitude is scaled into an unsigned 16-bit format, and the frequency is normalized with respect to the sampling rate and is scaled into signed 32-bit format (and is thus written to the "phase_inc" register of the block). The frequency and scale must be within their respective ranges of [0.0, 3.96e9] and [0.0,1.0].

Each BITE configuration also specifies the length of time, in seconds, of the Long Sequence Test Vector (LSTV) that that configuration will generate. This must be greater than 0.

Finally, each configuration specifies a "sample_rate_k" value, which is the k value that modifies the BITE sample rate according to this equation:

BITE Sample Rate = 3960000000 + k * 1800

where 1800 is the frequency offset delta f. 
The "lstv_seconds" and "sample_rate_k" will be used to determine the allocation of DDR4 memory required for storing the LSTV. Neither of these parameters is given a maximum value because they are constrained by the maximum size of the LSTV, which is 256GB, and so their maximum values would be inversely proportional. You can have a lot of samples over a short time span, or a long sample with few samples, etc. As a (rough) sanity check, the product of the length of the LSTV (in seconds) and the final k-value-modified sample rate cannot exceed 85228257260 without exceeding memory constraints.

Note:
* The `bite_initial_timestamp_time_offset` property in `bite_configs_json` is the initial timestamp of the generated BITE data, NOT the time the BITE is replayed.

### Filter Definitions
See examples in `filters.json`.

See [SciPy Window Types](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.get_window.html#scipy.signal.get_window) for the window definitions used in the filter definitions. 

### Future Functionality
SPFRx / receptor configuration file (like bite_configs).

----
## Delay Models

See `delay_model_package.json` in the `delay_model_package` folder for examples based on the Telescope Model schema: 
[ska-csp-delaymodel.html](https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-delaymodel.html).

----
## Scan Configurations
See `configure_scan.json` in the `configure_scan` folder for example scan configurations based on Telescope Model schema: [ska-csp-configure.html](https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-configure.html#csp-config-2-0)

----
## Mid.CBF InitSysParam
See `init_sys_param.json` in the `test_parameters` folder for example initsysparam parameters based on Telescope Model schema: [ska-mid-cbf-initsysparam.html](https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-mid-cbf-initsysparam.html#mid-cbf-parameters-1-0)
