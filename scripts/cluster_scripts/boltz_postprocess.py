#!/usr/bin/python3

import os,sys
import csv, json, yaml
import numpy as np
from glob import glob

def compute_pae_int(pae_matrix, chains):
    """Compute pAE_int between chains from the given pae_matrix."""
    start_stop = []
    nres = 0
    for x in chains:
        start_stop.append([nres, nres + x])
        nres += x

    pAE_int = []
    chain_pairs = []
    chain_names = [chr(i + 65) for i in range(len(chains))]  # A, B, C, ...

    for i in range(len(chains)):
        for j in range(i + 1, len(chains)):  # Only off-diagonal pairs
            start_i = start_stop[i][0]
            stop_i = start_stop[i][1]
            start_j = start_stop[j][0]
            stop_j = start_stop[j][1]
            pae_ij = np.mean(pae_matrix[start_i:stop_i, start_j:stop_j])
            pae_ji = np.mean(pae_matrix[start_j:stop_j, start_i:stop_i])
            pAE_int.append(np.mean([pae_ij, pae_ji]))
            chain_pairs.append(f"boltz_pae_{chain_names[i]}{chain_names[j]}")

    return dict(zip(chain_pairs, pAE_int))  # Return as a dictionary for easy merging

def process_boltz_data(input_csv):
    """Check if expected Boltz results exist for each YAML file in the input directory."""
    input_folder = os.path.join(os.getcwd(), "input")
    rerun_list_file = os.path.join(os.getcwd(), "rerun_jobs.list")
    output_csv = os.path.splitext(input_csv)[0] + "_boltz.csv"  # Output CSV with extracted data

    # Ensure input folder exists
    if not os.path.isdir(input_folder):
        print(f"Error: Input directory '{input_folder}' does not exist.")
        sys.exit(1)

    # Get all YAML files in the input directory
    yaml_files = glob(os.path.join(input_folder, "*.yaml"))

    if not yaml_files:
        print("No YAML files found in the input directory.")
        sys.exit(1)

    missing_files = []
    rerun_jobs = []
    boltz_data_map = {}

    for yaml_path in yaml_files:
        yaml_name = os.path.basename(yaml_path)
        base_name = os.path.splitext(yaml_name)[0]  # Remove .yaml extension
        
        # Expected JSON result path
        json_path = os.path.join(
            f"boltz_results_{base_name}", "predictions", base_name, f"confidence_{base_name}_model_0.json"
        )

        pdb_path = os.path.abspath(
            os. path.join(
                f"boltz_results_{base_name}", "predictions", base_name, f"{base_name}_model_0.pdb"
            )
        )

        # Check if .npz exists for PAE
        npz_path = os.path.join(
            os.getcwd(), f"boltz_results_{base_name}", "predictions", base_name, f"pae_{base_name}_model_0.npz"
        )

        chains = []
        if not os.path.exists(json_path):
            missing_files.append(json_path)

            # Generate rerun command
            rerun_jobs.append(
                f"singularity run -B /runtime --nv /runtime/singularity_images/boltz1_cuda12_latest.sif "
                f"boltz predict --cache /runtime/databases/boltz1 --output_format pdb --use_msa_server "
                f"--diffusion_samples 5 --write_full_pae --override ./input/{base_name}.yaml"
            )
        else:
            # Extract relevant fields from JSON
            with open(json_path, 'r') as json_file:
                data = json.load(json_file)

                # Store extracted data for later merging
                boltz_data_map[base_name] = {
                    "boltz_confidence_score": data.get("confidence_score", None),
                    "boltz_ptm": data.get("ptm", None),
                    "boltz_iptm": data.get("iptm", None),
                    "boltz_complex_plddt": data.get("complex_plddt", None),
                    "boltz_complex_iplddt": data.get("complex_iplddt", None),
                    "boltz_complex_pde": data.get("complex_pde", None),
                    "boltz_complex_ipde": data.get("complex_ipde", None),
                    "boltz_pdb_path": pdb_path if os.path.exists(pdb_path) else None  # Store PDB file path
                }

                # Compute PAE if npz file exists
                if os.path.exists(npz_path):

                    # Extract chain lengths from YAML
                    with open(yaml_path, 'r') as yaml_file:
                        yaml_data = yaml.safe_load(yaml_file)
                        chain_lengths = [len(chain['protein']['sequence']) for chain in yaml_data['sequences']]
                        chains = chain_lengths

                    with np.load(npz_path) as npz_data:
                        pae_matrix = npz_data['pae']
                        pae_values = compute_pae_int(pae_matrix, chains)
                        boltz_data_map[base_name].update(pae_values)

    # Print results
    if missing_files:
        print("The following expected result files are missing:")
        for file in missing_files:
            job_name = os.path.basename(file).split("_model_0.json")[0].replace("confidence_", "")
            print(f"  - {job_name}")
        print(f"Results for {len(missing_files)} jobs were missing.")

        # Write rerun_jobs.list file
        with open(rerun_list_file, 'w') as rerun_file:
            rerun_file.write("\n".join(rerun_jobs) + "\n")

    else:
        print("All expected result files are present.")


    # Read input CSV and update it with extracted Boltz data
    updated_rows = []
    with open(input_csv, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames

        # Ensure the new fields exist in the CSV header
        all_pae_columns = set()
        for base_name in boltz_data_map:
            all_pae_columns.update(boltz_data_map[base_name].keys())

        for col in sorted(all_pae_columns):
            if col not in fieldnames:
                fieldnames.append(col)

        for row in reader:
            design_name = row.get("omegafold_input_name", "").strip()
            if design_name in boltz_data_map:
                row.update(boltz_data_map[design_name])  # Merge extracted data
            updated_rows.append(row)

    # Write updated CSV with new data
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"Updated CSV with Boltz results: {output_csv}")


if __name__ == "__main__":
    # Ensure correct usage with two arguments
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_csv>")
    else:
        input_csv = sys.argv[1]
        process_boltz_data(input_csv)

