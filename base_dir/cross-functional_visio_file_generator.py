import os
import fire
import pandas as pd
import numpy as np
import treelib

INPUTFILES = {
    "network topology" : "network-topology.json",
    "devices" : "device.json"}

OUTPUTFILE = 'Domotz Network Topology (cross-functional)'

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
    work_df = merged_df[merged_df["status"] == 'ONLINE'] \
        [list(DEVICE_INFO_MAP.keys())].copy()

    work_df["type"] = work_df["type"].apply(lambda x: x['label'])

    work_df.rename(inplace=True, columns=DEVICE_INFO_MAP)

    # Rebuiling network topology trees
    dev_roots, dev_trees = get_device_trees(work_df)

    # Counting total descendent devices of the root devices
    dev_childs_df = work_df[work_df["Connected to Device ID"].isin(dev_roots)] \
        .groupby(by="Connected to Device ID").size().reset_index(name='Devices') \
        .rename(columns={"Connected to Device ID" : "Root Device ID"})

    # Evaluating tree depth of each root device
    depth_list = []
    for r in  dev_roots:
        depth_list.append([r, dev_trees[r].depth()])

    depth_df = pd.DataFrame(depth_list, columns =["Root Device ID", "Depth"])

    # Joining info of total descendent devices and tree depth and sorting from
    # by deepest and most childs
    dev_root_df = pd.merge(depth_df, dev_childs_df, 
        how="left", on="Root Device ID").fillna(0)

    dev_root_df["Device Root Rank"] = dev_root_df[["Depth", "Devices"]] \
        .apply(tuple,axis=1).rank(method='dense',ascending=False).astype(int)

    dev_root_df.sort_values(by="Device Root Rank", ignore_index=True, inplace=True)

    # Evaluating the phase: a different tree is a different pahse and the latest
    # phase contains the floating devices
    dev_root_df["Phase"] = np.arange(1, dev_root_df.shape[0] + 1)

    max_r = max(dev_root_df[dev_root_df["Depth"] > 0]["Phase"]) + 1

    dev_root_df["Phase"] = dev_root_df.apply(
        lambda x: x["Phase"] if x["Depth"] > 0 else max_r, axis=1).astype(int)

    # Evaluating the function as the depth in each tree
    func_list = []

    for dev_root in dev_roots:
        tree = dev_trees[dev_root]
        
        for node in tree.expand_tree(mode=treelib.Tree.DEPTH):
            try:
                dev_parent = int(tree.parent(node).tag)
            except AttributeError:
                dev_parent = None
            
            func_list.append([
                int(tree[node].tag), 
                tree.level(node), 
                dev_parent, 
                dev_root])

    function_df = pd.DataFrame(func_list, columns=[
        "Device ID", 
        "Function", 
        "Connected to Device ID", 
        "Root Device ID"])

    # Joning the function and phase infos and sorting
    func_phase_df = pd.merge(function_df, dev_root_df, how='left', 
        on="Root Device ID")

    func_phase_df.sort_values(by=[
        "Phase", 
        "Function", 
        "Connected to Device ID", 
        "Device ID"], 
        ignore_index=True, inplace=True)

    # Shaping the final dataframe for the output file
    final_df = pd.merge(
        func_phase_df[["Device ID", "Function", "Phase"]],
        work_df,
        how='left', on="Device ID")

    final_df = final_df[[
        *list(DEVICE_INFO_MAP.values())[:4], 
        "Function", "Phase",
        *list(DEVICE_INFO_MAP.values())[4:]]]

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


# It takes in input a dataframe with "Connected to Device ID" and "Device ID" 
# and returns the list of root devices and a dictionary containing tree objects 
# for each root device of the network topology 

def get_device_trees(df):

    # Returns the list of root devices and a list of trees for each of them
    def _get_roots(df):
        root_list = df[pd.isna(df["Connected to Device ID"])]["Device ID"] \
            .dropna().unique().tolist()

        trees = dict()
        for root in root_list:
            trees[root] = treelib.Tree()
            trees[root].create_node(str(root), root)

        return root_list, trees

    # Given a list of parent devices populates the tree with their childs and
    # returns the list of the latters
    def _get_host_devices(df, tree, parent_list):
        for parent in parent_list:
            child_list = df[df["Connected to Device ID"] == parent] \
                ["Device ID"].dropna().unique().tolist()

            if len(child_list) > 0:
                for child in child_list:
                    tree.create_node(str(child), child, parent=parent)
                    leaf = 0
            else:
                leaf = 1
        return leaf, child_list

    roots, trees = _get_roots(df)

    for r in roots:
        leaf = 0
        parents = [r]

        while leaf == 0:
            leaf, parents = _get_host_devices(df, trees[r], parents)
        
    return roots, trees


if __name__ == '__main__':
    fire.Fire(main)