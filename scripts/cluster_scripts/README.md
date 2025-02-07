# Scripts for pipeline setup and analysis of Boltz jobs

## Basics

These scripts help to generate and run input for Boltz structure predictions on the GCE cluster as part of standard deisng pipeline. This assumes you are working with a csv that gets passed from step to step, accumulating extra data from each successive piece of software. Thus, the input is a csv with your sequences and the output is an edited version of your original csv, but with extra columns indicating the Boltz metrics for the structure prediction.

**1.) setup**

> ./boltz_setup.py [ input csv ]

**2.) job launch**

> ./slurm_submit.sh

**3.) post processing**

> ./postprocess_boltz.py [ original csv ]

## Input notes

Currently the script expects to find two columns in your input CSV:

1.) `omegafold_input_name` [[code]](https://github.com/ZipBioTx/boltz/blob/df27f97fd933e360677b91f52321625d997dd631/scripts/cluster_scripts/boltz_setup.py#L46)

2.) `seq` or `sequence` [[code]](https://github.com/ZipBioTx/boltz/blob/df27f97fd933e360677b91f52321625d997dd631/scripts/cluster_scripts/boltz_setup.py#L36)

The script should fail if either of these columns are not found.

For each design, a yaml input file will be generated for prediction by Boltz in a `input` folder. If the sequence has multiple chains as indicated by `/` characters, this will be automatically handled.

One all the input yamls are generated, the setup script will output a `slurm_submit.sh` script to launch the jobs on the l4spt cluster (which predicts structure ~2x faster than on gpuspot).

## Output notes

Output is generating in a folder with the same name as the `omegafold_input_name`, but preceeded by `boltz_results_`.

The postprocessing script will append the following columns to your input CSV:

1.) **boltz_confidence_score** -- a metric created by the Boltz developers: 0.8 * complex_plddt + 0.2 * ipTM, where ipTM is substituted with the pTM for single chain structures

2.) **boltz_ptm** -- global fold confidence (0-1 scale)

3.) **boltz_iptm** -- interface confidience (0-1 scale)

4.) **boltz_complex_plddt** -- average local confidence per residue (0-100 scale)

5.) **boltz_complex_iplddt** -- average local confidence at the interface (0-100 scale)

6.) **boltz_complex_pde** -- docking error (global) (values vary, lower is better)

7.) **boltz_complex_ipde** -- docking error (interface) (values vary, lower is better)

8.) **boltz_pdb_path** -- absolute path of structure with highest confidence value

9.) **boltz_pae_AB** -- pae_int for all possible interfaces of the complex

The input script has added the `--write_full_pae` flag to force the writing of the pae matrix, which is then used to compute the pae_int values between all chain combinations.

Similar to the setup script, the postprocess script once again expects to find a `omegafold_input_name` [[code]](https://github.com/ZipBioTx/boltz/blob/df27f97fd933e360677b91f52321625d997dd631/scripts/cluster_scripts/boltz_postprocess.py#L148) column in your input csv for proper mapping of the Boltz data back to the output csv.
 
