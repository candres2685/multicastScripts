import re
import json
import time
import datetime
import subprocess
from netmiko import ConnectHandler


def get_router_output(router, cmd):

    '''
    Takes in a cmd and router then returns the output
    '''
    conn_params = {
        'host': router,
        'username': "Lab_User",
        'password': "Lab_User",
        'banner_timeout': 60,
        'device_type': 'cisco_ios'
        }

    ssh = ConnectHandler(**conn_params)
    return ssh.send_command(cmd)


def get_device_cdp_neighbors(router):

    '''
    Takes in a router and returns the CDP neighbors and their associated interfaces
    '''
    cdp_output = get_router_output(router, "show cdp neighbors detail")
    cdp_regex = "Device ID\:\s(\S+?)\.\S+\n.*\n.*\n.*\n.*Interface: (\S+)\,\D+port\)\:\s(\S+)"
    cdp_matches = re.compile(cdp_regex).findall(cdp_output)

    return cdp_matches


def get_device_neighbor_dict(router, all_host_dict):

    '''
    Converts CDP matches into a dictionary
    '''

    all_host_dict.update({f"{router}": {}})
    cdp_matches = get_device_cdp_neighbors(router)
    for remote_host, local_int, remote_int in cdp_matches:
        cdp_dict = {
            f"{local_int}": {
                "Remote Hostname": remote_host,
                "Remote Interface": remote_int
            }
        }
        all_host_dict[f"{router}"].update(cdp_dict)

    return all_host_dict


def get_device_neighbor_list(all_host_dict, neighbor_list):

    '''
    Takes in a all_host_dict and returns a list of neighboring devices
    '''

    for device, device_details in all_host_dict.items():
        for local_int, local_int_details in device_details.items():
            neighbor_list.append(local_int_details["Remote Hostname"])

    return neighbor_list


def build_path(initial_router):

    '''
    Builds the entire path using CDP
    '''

    all_host_dict = dict()
    neighbor_list = list()
    iterated_list = list()

    # First Iteration
    all_host_dict = get_device_neighbor_dict(initial_router, all_host_dict)
    iterated_list.append(initial_router)
    neighbor_list = get_device_neighbor_list(all_host_dict, neighbor_list)

    # Subsequent Iterations
    while len(neighbor_list) != 0:
        current_router = neighbor_list[0]
        all_host_dict = get_device_neighbor_dict(router=current_router, all_host_dict=all_host_dict)
        iterated_list.append(current_router)
        neighbor_list = list(set(get_device_neighbor_list(all_host_dict, neighbor_list)).difference(set(iterated_list)))

    return all_host_dict


def build_tree(all_host_dict, group_ip, source_ip):

    '''
    Builds the multicast tree using mroute output
    '''

    for device, device_details in all_host_dict.items():

        mroute_output = get_router_output(
            router=device, 
            cmd=f"show ip mroute {source_ip} {group_ip}"
            )

        incoming_interface_regex = "\:\s(\S+)\,\sRPF"
        incoming_interface_matches = re.compile(incoming_interface_regex).findall(mroute_output)

        outgoing_interface_regex = "\s+(\S+)\,\sFor"
        outgoing_interface_matches = re.compile(outgoing_interface_regex).findall(mroute_output)

        local_int_list = device_details.keys()
        for intfc in local_int_list:
            if incoming_interface_matches != []:
                if intfc == incoming_interface_matches[0]:
                    device_details[intfc].update({"Incoming Interface": "Yes"})
            if outgoing_interface_matches != []:
                for out_int in outgoing_interface_matches:
                    if intfc == out_int:
                        device_details[intfc].update({"Outgoing Interface": "Yes"})
    
    return all_host_dict


def get_multicast_count(all_host_dict, group_ip, source_ip):

    '''
    Updates each device in the all_host_dict with the multicast traffic details
    '''
    
    for device, device_details in all_host_dict.items():

        first_mroute_count_output = get_router_output(
            router=device, 
            cmd=f"show ip mroute {source_ip} {group_ip} count"
            )

        time.sleep(30)

        second_mroute_count_output = get_router_output(
            router=device, 
            cmd=f"show ip mroute {source_ip} {group_ip} count"
            )

        mroute_count_regex = ", Packets forwarded: (\d+), Packets received: (\d+)"

        first_mroute_count_matches = re.compile(mroute_count_regex).findall(first_mroute_count_output)
        if first_mroute_count_matches != []:
            first_packets_forwarded = first_mroute_count_matches[0][0]
            first_packets_received = first_mroute_count_matches[0][1]

        second_mroute_count_matches = re.compile(mroute_count_regex).findall(second_mroute_count_output)
        if second_mroute_count_matches != []:
            second_packets_forwarded = second_mroute_count_matches[0][0]
            second_packets_received = second_mroute_count_matches[0][1]

        packets_forwarded_delta = int(second_packets_forwarded) - int(first_packets_forwarded)
        packets_received_delta = int(second_packets_received) - int(first_packets_received)

        for local_int, local_int_details in device_details.items():

            try:
                if local_int_details["Incoming Interface"] == "Yes":
                    if packets_received_delta > 0:
                        local_int_details.update({"Active Traffic": "Yes"})
            except:
                try:
                    if local_int_details["Outgoing Interface"] == "Yes":
                        if packets_forwarded_delta > 0:
                            local_int_details.update({"Active Traffic": "Yes"})
                except:
                    continue
            finally:
                continue

    return all_host_dict


def notate_bifurcation(all_host_dict):

    '''
    Marks the multicast tree with bifurcation points
    '''

    for device, device_details in all_host_dict.items():

        local_int_count = 0
        for local_int, local_int_details in device_details.items():
            try:
                if local_int_details["Outgoing Interface"] == "Yes":
                    local_int_count += 1
            except:
                continue
        if local_int_count > 1:
            device_details.update({"Bifurcation Point": "Yes"})

    return all_host_dict


if __name__ == '__main__':



    # Builds the path
    initial_router = "SEA-CORE"
    all_host_dict = build_path(initial_router)

    # Builds the multicast tree
    group_ip = "239.1.1.1"
    source_ip = "1.1.1.1"
    all_host_dict = build_tree(all_host_dict, group_ip, source_ip)

    # Specifies which interfaces have active traffic
    all_host_dict = get_multicast_count(all_host_dict, group_ip, source_ip)

    # Notates bifurcation points
    all_host_dict = notate_bifurcation(all_host_dict)

    # Writes the JSON output
    now = datetime.datetime.now()
    file_name = f"multicastMapOutput-{str(now.strftime('%Y-%m-%d-%H%M%S'))}.json"
    touch_cmd = f"touch {file_name}"
    subprocess.Popen(touch_cmd, shell=True,
        stdout=subprocess.PIPE, universal_newlines=True).communicate()[0]
    perm_cmd = f"chmod 777 /home/candres/candres_scripts/multicast_tree/{file_name}"
    subprocess.Popen(perm_cmd, shell=True,
        stdout=subprocess.PIPE, universal_newlines=True).communicate()[0]
    with open(f"/home/candres/candres_scripts/multicast_tree/multicastMapOutput-{str(now.strftime('%Y-%m-%d-%H%M%S'))}.json", 'a') as output:
        output.write(json.dumps(all_host_dict, indent=3))

