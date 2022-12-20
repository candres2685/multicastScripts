"""
This script maps the network path by parsing CDP output and then storing the connections.
The script will then update a dictionary notating the multicast interfaces, whether a device
is considered a bifurcation point and whether a multicast interface has active traffic.
This data can then be used to create a visualization of a multicast tree showing where multicast
traffic is flowing in the network. 

This scripts requires inputs of username, password, initial router, and multicast group and source IPs
"""

import json
import datetime
import subprocess
import argparse

from multicast.networkMap import Network
from multicast.growTree import TreeGrower


if __name__ == '__main__':

    # Defines Parser Arguments such as username, password, initial router (e.g. SEA-CORE), group ip (e.g. 239.1.1.1) and source ip (e.g. 1.1.1.1)
    parser = argparse.ArgumentParser(prog = 'MulticastMapper', description = 'Creates multicast tree map')
    parser.add_argument('-u', '--username')
    parser.add_argument('-p', '--password')
    parser.add_argument('-i', '--initial_router')
    parser.add_argument('-s', '--source_ip')
    parser.add_argument('-g', '--group_ip')
    args = parser.parse_args()

    # Creates Network Class Instance
    networkMap = Network(initial_router=args.initial_router, username=args.username, password=args.password)

    # Creates TreeGrower Class Instance
    multicastTree = TreeGrower(group_ip=args.group_ip, source_ip=args.source_ip, username=args.username, password=args.password)

    # Builds the Network Map
    all_host_dict = networkMap.build_path(initial_router=args.initial_router)

    # Builds the multicast tree
    all_host_dict = multicastTree.build_tree(all_host_dict)

    # Specifies which interfaces have active traffic
    all_host_dict = multicastTree.get_multicast_count(all_host_dict)

    # Notates bifurcation points
    all_host_dict = multicastTree.notate_bifurcation(all_host_dict)

    # Writes the JSON output to a file
    now = datetime.datetime.now()

    file_name = f"multicastMapOutput-{str(now.strftime('%Y-%m-%d-%H%M%S'))}.json"
    folder_name = "/home/candres/candres_scripts/multicast_tree/"    
    path = f"{folder_name}{file_name}"

    touch_cmd = f"touch {path}"
    perm_cmd = f"chmod 777 {path}"

    subprocess.Popen(touch_cmd, shell=True,
        stdout=subprocess.PIPE, universal_newlines=True).communicate()[0]
    subprocess.Popen(perm_cmd, shell=True,
        stdout=subprocess.PIPE, universal_newlines=True).communicate()[0]

    with open(f"{path}", 'a') as output:
        output.write(json.dumps(all_host_dict, indent=3))

