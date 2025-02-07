#!/usr/bin/python3

import os,sys
import csv
import yaml
import string

cwd = os.getcwd()

# Ensure script is called with correct arguments
if len(sys.argv) < 2:
    sys.exit('Usage: ./script.py [design.csv]')

input_csv = sys.argv[1]
input_folder = os.path.join(cwd, "input")
job_list_file = os.path.join(os.getcwd(), "job.list")

# Create output folder if it doesn't exist
os.makedirs(input_folder, exist_ok=True)


def get_column_names(filename):
    try:
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            return headers
    except IOError as e:
        print('Error opening the file: {}'.format(e))
        return []

col_names = get_column_names(input_csv)

# Identify column indicies for input CSV
try:
    if 'sequence' in col_names:
        seq_index = col_names.index('sequence')
    elif 'seq' in col_names:
        seq_index = col_names.index('seq')
    else:
        raise ValueError("Neither 'sequence' nor 'seq' column found in the input CSV.")
except ValueError as e:
    print(e)
    sys.exit(1)

name_index = col_names.index('omegafold_input_name')

job_list_entries = []

# Read CSV and generate YAML files
with open(input_csv, 'r') as f:
    reader = csv.reader(f)
    next(reader)  # Skip header

    for row in reader:
        design_name = row[name_index]
        sequence_data = row[seq_index]

        # Split sequence by '/' to determine chains
        sequences = sequence_data.split('/')
        yaml_data = {"sequences": [], "version": 1}

        for i, seq in enumerate(sequences):
            chain_id = string.ascii_uppercase[i]  # Assign chain ID (A, B, C, ...)
            yaml_data["sequences"].append({
                "protein": {
                    "id": chain_id,
                    "sequence": seq.strip()
                }
            })

        # Write YAML to input folder
        yaml_filename = os.path.join(input_folder, f"{design_name}.yaml")
        with open(yaml_filename, 'w') as yaml_file:
            yaml.dump(yaml_data, yaml_file, default_flow_style=False)

        print(f"Written: {yaml_filename}")

        # Add job list entry
        job_list_entries.append(
            #f"singularity run -B /runtime --nv /runtime/singularity_images/boltz1_cuda12_latest.sif "
            #f"boltz predict --cache /runtime/databases/boltz1 --output_format pdb --use_msa_server "
            f"/runtime/scripts/boltz.sh predict --cache /runtime/databases/boltz1 --output_format pdb --use_msa_server "
            f"--diffusion_samples 5 --write_full_pae --override ./input/{design_name}.yaml"
        )


# Write job.list file
with open(job_list_file, 'w') as job_file:
    job_file.write("\n".join(job_list_entries) + "\n")

print(f"Written: {job_list_file}")


fout = open('slurm_submit.sh','w')
fout.write('#!/bin/sh\n\n')
fout.write('/runtime/scripts/slurm_submit_joblist -p l4spt -m 8G -c 1 -f %s/job.list'%(cwd))
fout.close()

