# Generators of Visio Excel files for basic and cross-functional templates

These scripts generates a .xlsx file that can be used as input for the Domotz Network Topology templates for Microsoft Visio.

Ass inputs requires two json files containing:

* the network topology
* the device information

## Requirements

Python 3.8.1+

* fire==0.4.0
* pandas==1.0.4
* numpy==1.18.4
* treelib==1.6.1

## Folder Organization

By default, both scripts expect the following folter organization:

* base_dir : script folder
* input_files: folder containing the network topology and devices JSON files
* output_files: folder where the output file will be saved

## Arguments

Both scripts accept in input the following optional arguments:

* network_topology: path to the JSON file containing the network topology
* devices: path to the JSON file containing the device information
* outfile: path to the output file to be saved
