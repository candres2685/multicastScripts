import re

from netmiko import ConnectHandler


class Network():
    '''
    This class creates a network map using CDP
    '''

    def __init__(self, initial_router, username, password):
        self.initial_router = initial_router
        self.username = username
        self.password = password

    def get_router_output(self, router, cmd, username, password):

        '''
        Takes in a cmd and router then returns the output
        '''
        conn_params = {
            'host': router,
            'username': self.username,
            'password': self.password,
            'banner_timeout': 60,
            'device_type': 'cisco_ios'
            }

        ssh = ConnectHandler(**conn_params)
        return ssh.send_command(cmd)


    def get_device_cdp_neighbors(self, router):

        '''
        Takes in a router and returns the CDP neighbors and their associated interfaces
        '''
        cdp_output = self.get_router_output(router, "show cdp neighbors detail", self.username, self.password)
        cdp_regex = "Device ID\:\s(\S+?)\.\S+\n.*\n.*\n.*\n.*Interface: (\S+)\,\D+port\)\:\s(\S+)"
        cdp_matches = re.compile(cdp_regex).findall(cdp_output)

        return cdp_matches


    def get_device_neighbor_dict(self, router, all_host_dict):

        '''
        Converts CDP matches into a dictionary
        '''

        all_host_dict.update({f"{router}": {}})
        cdp_matches = self.get_device_cdp_neighbors(router)
        for remote_host, local_int, remote_int in cdp_matches:
            cdp_dict = {
                f"{local_int}": {
                    "Remote Hostname": remote_host,
                    "Remote Interface": remote_int
                }
            }
            all_host_dict[f"{router}"].update(cdp_dict)

        return all_host_dict


    def get_device_neighbor_list(self, all_host_dict, neighbor_list):

        '''
        Takes in a all_host_dict and returns a list of neighboring devices
        '''

        for device, device_details in all_host_dict.items():
            for local_int, local_int_details in device_details.items():
                neighbor_list.append(local_int_details["Remote Hostname"])

        return neighbor_list


    def build_path(self, initial_router):

        '''
        Builds the entire path using CDP
        '''

        all_host_dict = dict()
        neighbor_list = list()
        iterated_list = list()

        # First Iteration
        all_host_dict = self.get_device_neighbor_dict(initial_router, all_host_dict)
        iterated_list.append(initial_router)
        neighbor_list = self.get_device_neighbor_list(all_host_dict, neighbor_list)

        # Subsequent Iterations
        while len(neighbor_list) != 0:
            current_router = neighbor_list[0]
            all_host_dict = self.get_device_neighbor_dict(router=current_router, all_host_dict=all_host_dict)
            iterated_list.append(current_router)
            neighbor_list = list(set(self.get_device_neighbor_list(all_host_dict, neighbor_list)).difference(set(iterated_list)))

        return all_host_dict
