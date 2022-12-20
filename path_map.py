import json
import datetime
import subprocess

from networkMap import Network
from growTree import TreeGrower


if __name__ == '__main__':


    # Defines the initial router
    initial_router="SEA-CORE"

    # Creates Network Class Instance
    networkMap = Network(initial_router=initial_router)

    # Creates TreeGrower Class Instance
    multicastTree = TreeGrower(group_ip="239.1.1.1", source_ip="1.1.1.1")

    # Builds the Network Map
    all_host_dict = networkMap.build_path(initial_router=initial_router)

    # Builds the multicast tree
    all_host_dict = multicastTree.build_tree(all_host_dict)

    # Specifies which interfaces have active traffic
    all_host_dict = multicastTree.get_multicast_count(all_host_dict)

    # Notates bifurcation points
    all_host_dict = multicastTree.notate_bifurcation(all_host_dict)

    # Writes the JSON output to a file
    now = datetime.datetime.now()

    file_name = f"multicastMapOutput-{str(now.strftime('%Y-%m-%d-%H%M%S'))}.json"
    
    touch_cmd = f"touch {file_name}"
    perm_cmd = f"chmod 777 /home/candres/candres_scripts/multicast_tree/{file_name}"

    subprocess.Popen(touch_cmd, shell=True,
        stdout=subprocess.PIPE, universal_newlines=True).communicate()[0]
    subprocess.Popen(perm_cmd, shell=True,
        stdout=subprocess.PIPE, universal_newlines=True).communicate()[0]

    with open(f"/home/candres/candres_scripts/multicast_tree/multicastMapOutput-{str(now.strftime('%Y-%m-%d-%H%M%S'))}.json", 'a') as output:
        output.write(json.dumps(all_host_dict, indent=3))

