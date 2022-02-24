import os
import fire
import pandas as pd
import numpy as np

INPUTFILES = {
    "network topology" : "network-topology.json",
    "devices" : "device.json"}

OUTPUTFILE = 'Domotz Network Topology (basic)'

ENTITYNAME = 'Network_Topology'

DEVICE_INFO_MAP = {
    "id" : "Device ID",
    "name" : "Device Name",
    "host_device_id" : "Connected to Device ID",
    "type" : "Device Type",
    "model" : "Model",
    "vendor" : "Vendor",
    "ip" : "IP",
    "mac" : "MAC"}

BASEDIR = os.getcwd()
INPUTDIR = os.path.join(BASEDIR, os.pardir, 'input_files') 
OUTPUTDIR = os.path.join(BASEDIR, os.pardir, 'output_files')

DEFAULT_NETWORK_TOPOLOGY = os.path.join(INPUTDIR, INPUTFILES["network topology"])
DEFAULT_DEVICES = os.path.join(INPUTDIR, INPUTFILES["devices"])
DEFAULT_OUTPUT = os.path.join(OUTPUTDIR, OUTPUTFILE + '.xlsx')


## --------------------------------- MAIN ----------------------------------- ##

def main(network_topology=DEFAULT_NETWORK_TOPOLOGY, devices=DEFAULT_DEVICES,
    outfile=DEFAULT_OUTPUT):

    # Importing the device and network topology data from json files
    net_topology_df = pd.read_json(network_topology)
    devices_df = pd.read_json(devices)

    # Filtering out host devices and the devices connected to with status 
    # different from ONLINE
    online_devices = devices_df[devices_df["status"] == 'ONLINE']["id"].tolist()

    online_net_top_df = net_topology_df[
        (net_topology_df["attached_device_id"].isin(online_devices)) & 
        (net_topology_df["host_device_id"].isin(online_devices))]

    # Removing duplicated liks in the network topology (host device with min id 
    # is keept)
    cleaned_online_net_top_df = remove_link_duplicates(online_net_top_df)

    # Joining device information and network topology map
    merged_df = pd.merge(devices_df, cleaned_online_net_top_df, how='left', 
        left_on='id', right_on='attached_device_id')

    # Shaping the dataframe for creating the final excel file
    final_df = merged_df[merged_df["status"] == 'ONLINE'] \
        [list(DEVICE_INFO_MAP.keys())].copy()

    final_df["type"] = final_df["type"].apply(lambda x: x['label'])

    final_df.rename(inplace=True, columns=DEVICE_INFO_MAP)

    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter(outfile, engine='xlsxwriter')

    final_df.to_excel(writer, sheet_name=ENTITYNAME, startrow=1, header=False, 
        index=False)

    # Get the xlsxwriter workbook and worksheet objects.
    workbook = writer.book
    worksheet = writer.sheets[ENTITYNAME]

    # Get the dimensions of the dataframe.
    (max_row, max_col) = final_df.shape

    # Create a list of column headers, to use in add_table().
    column_settings = []
    for header in final_df.columns:
        column_settings.append({'header': header})

    # Add the table.
    worksheet.add_table(0, 0, max_row, max_col - 1, {
        'columns': column_settings, 
        'name': ENTITYNAME})

    # Make the columns wider for clarity.
    worksheet.set_column(0, max_col - 1, 12)

    # Close the Pandas Excel writer and output the Excel file.
    writer.save()

## ------------------------------- FUNCTIONS -------------------------------- ##


# It takes as input a dataframe and removes the one of the rows relative to 
# duplicated links between the same couple of devices giving priority to the 
# link where the host device has the smallest id

def remove_link_duplicates(df):
    temp_df = df.copy()

    temp_df["link"] = temp_df.apply(lambda x: 
        np.array2string(
            np.sort(
                np.array([
                    x["attached_device_id"], 
                    x["host_device_id"]]), 
                axis=0)), axis=1)

    temp_df["rank"] = temp_df.groupby(by="link")["host_device_id"].rank("dense")
    res_df = temp_df[temp_df["rank"] == 1].drop(columns=["link", "rank"])
        
    return res_df.copy()


if __name__ == '__main__':
    fire.Fire(main)