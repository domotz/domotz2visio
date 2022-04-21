# Generators of Visio Excel files for basic and cross-functional templates

These scripts generates a .xlsx file that can be used as input for the Domotz Network Topology templates for Microsoft Visio.

As inputs requires two json files containing:

* the network topology
* the device information

N.B. input_files and output_files directories MUST be created

## Requirements

Python 3.8.1+

For py libraries, check file requirements.txt
## Folder Organization

By default, both scripts expect the following folder organization:

* base_dir : script folder
* input_files: folder containing the network topology and devices JSON files
* output_files: folder where the output file will be saved

## Arguments

Both scripts accept in input the following optional arguments:

* network_topology: path to the JSON file containing the network topology
* devices: path to the JSON file containing the device information
* outfile: path to the output file to be saved
