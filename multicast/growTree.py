import re
import time

from multicast.networkMap import Network


class TreeGrower():

    '''
    This class maps out the multicast tree and 
    notates where's there's active traffic
    '''


    def __init__(self, group_ip, source_ip, username, password):
        self.group_ip = group_ip
        self.source_ip = source_ip
        self.username = username
        self.password = password


    def build_tree(self, all_host_dict):

        '''
        Builds the multicast tree using mroute output
        '''

        for device, device_details in all_host_dict.items():
            cmd = f"show ip mroute {self.source_ip} {self.group_ip}"
            mroute_output = Network.get_router_output(self, router=device, 
                cmd=cmd, username=self.username, password=self.password)

            in_reg, out_reg = ["\:\s(\S+)\,\sRPF", "\s+(\S+)\,\sFor"]
            incoming_interface_matches = re.compile(in_reg).findall(mroute_output)
            outgoing_interface_matches = re.compile(out_reg).findall(mroute_output)

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


    def get_mroute_count(self, device):

        '''
        Returns the output of the mroute count command
        '''

        cmd = f"show ip mroute {self.source_ip} {self.group_ip} count"
        return Network.get_router_output(self, router=device, 
            cmd=cmd, username=self.username, password=self.password) 


    def get_mrt_cnt_matches(self, fwd_slice, rec_slice, output, reg):

        '''
        Returns the mroute 'show ip mroute count' packet counts
        '''

        mroute_count_matches = re.compile(reg).findall(output)
        if mroute_count_matches != []:
            pkts_fwd = mroute_count_matches[0][fwd_slice]
            pkts_rec = mroute_count_matches[0][rec_slice]

        return pkts_fwd, pkts_rec


    def get_multicast_count(self, all_host_dict):

        '''
        Updates each device in the all_host_dict with the multicast traffic details
        '''
        
        for device, device_details in all_host_dict.items():

            mrt_cnt_out_1 = self.get_mroute_count(device)
            time.sleep(5)
            mrt_cnt_out_2 = self.get_mroute_count(device)

            mrt_reg = ", Packets forwarded: (\d+), Packets received: (\d+)"

            pkts_fwd_1, pkts_rec_1 = \
                self.get_mrt_cnt_matches(0, 1, mrt_cnt_out_1, mrt_reg)
            pkts_fwd_2, pkts_rec_2 = \
                self.get_mrt_cnt_matches(0, 1, mrt_cnt_out_2, mrt_reg)

            pkts_fwd_delta = int(pkts_fwd_2) - int(pkts_fwd_1)
            pkts_rec_delta = int(pkts_rec_2) - int(pkts_rec_1)

            for local_int, local_int_details in device_details.items():

                try:
                    if local_int_details["Incoming Interface"] == "Yes":
                        if pkts_rec_delta > 0:
                            local_int_details.update({"Active Traffic": "Yes"})
                except:
                    try:
                        if local_int_details["Outgoing Interface"] == "Yes":
                            if pkts_fwd_delta > 0:
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


