import re
import time

from networkMap import Network


class TreeGrower():
    '''
    This class maps out the multicast tree and 
    notates where's there's active traffic
    '''


    def __init__(self, group_ip, source_ip):
        self.group_ip = group_ip
        self.source_ip = source_ip


    def build_tree(self, all_host_dict):

        '''
        Builds the multicast tree using mroute output
        '''

        for device, device_details in all_host_dict.items():

            mroute_output = Network.get_router_output(
                self,
                router=device, 
                cmd=f"show ip mroute {self.source_ip} {self.group_ip}"
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


    def get_multicast_count(self, all_host_dict):

        '''
        Updates each device in the all_host_dict with the multicast traffic details
        '''
        
        for device, device_details in all_host_dict.items():

            first_mroute_count_output = Network.get_router_output(self, router=device, 
                cmd=f"show ip mroute {self.source_ip} {self.group_ip} count")

            time.sleep(30)

            second_mroute_count_output = Network.get_router_output(self, router=device, 
                cmd=f"show ip mroute {self.source_ip} {self.group_ip} count")

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


    def notate_bifurcation(self, all_host_dict):

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


