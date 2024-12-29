from queue import Queue
import math
from collections import defaultdict

import yaml
import simpy
import numpy as np
import matplotlib.pyplot as plt

from components.system import Resource
from components.system.IS import IS
from components.system.IS_segmented import IS_segmented
from components.system.FIFO import FIFO
from components.system.FIFO_segmented import FIFO_segmented
from components.system.FIFO_sequential import FIFO_sequential
from components.users import User
from components.users.standard import UserStandard
from components.users.premium import UserPremium
from components.users.vip import UserVIP


def load_file(filename):
    with open(filename, 'r') as file:
        return yaml.safe_load(file)


class Net:
    
    def __init__(self, config: dict) -> None:
        self.config = config
        self.time = config['simulation']['time']
        self.avg_arrival_time = config['user']['avg_arrival_time']
        self.users_dict = [
            {
                'class': UserStandard,
                'type': 'standard'
            },
            {
                'class': UserPremium,
                'type': 'premium',
            },
            {
                'class': UserVIP,
                'type': 'VIP',
            }
        ]
        self.arrival_user_wages = []
        for user in self.users_dict:
            user_config = config['user'][user['type']]
            user['config'] = user_config
            self.arrival_user_wages.append(user_config['arrival_wage'])
        self.users = Queue()
        self.net_data = Queue()  # czasy użytkowników

        self.env = simpy.Environment()
        self.IS_input = IS(self.env, config['IS_input'])
        self.FIFO_sequential = FIFO_sequential(self.env, config['FIFO_sequential'])
        self.IS_between_servers = IS(self.env, config['IS_between_servers'])
        self.FIFO = FIFO(self.env, config['FIFO'])
        self.FIFO_segmented = FIFO_segmented(self.env, config['FIFO_segmented'])
        self.IS_segmented = IS_segmented(self.env, config['IS_segmented'])
        self.IS_output = IS(self.env, config['IS_output'])
        self.resources = (
            (self.IS_input, 'IS_input'), 
            (self.FIFO_sequential, 'FIFO_sequential'),  
            (self.IS_between_servers, 'IS_between_servers'), 
            (self.FIFO, 'FIFO'), 
            (self.FIFO_segmented, 'FIFO_segmented'), 
            (self.IS_segmented, 'IS_segmented'), 
            (self.IS_output, 'IS_output')
        )

    def create_user(self):
        selected_user_dict = np.random.choice(self.users_dict, 1, p=self.arrival_user_wages)[0]
        user = selected_user_dict['class'](selected_user_dict['config'])
        return user
    
    def register_time(self, user: User, time: float, is_entrance: bool):
        self.net_data.put((time, user, is_entrance))

    def flow(self, user: User):
        self.register_time(user, self.env.now, True)
        file_size = abs(np.random.normal(user.mean_file_size))

        if isinstance(user, UserVIP):       
            full_segments_number = math.floor(file_size / self.FIFO_segmented.segment_size)
            segments = [self.FIFO_segmented.segment_size for _ in range(full_segments_number)]

            for segment in segments:
                user.enter(self.env.now)
                yield self.IS_input.process(user)
                yield self.FIFO_sequential.process(user)
                yield self.IS_between_servers.process(user)

                download_time = segment / user.mean_download_speed
                yield self.FIFO_segmented.process(user, download_time)
                yield self.IS_output.process(user)
                user.out(self.env.now)
                yield self.IS_segmented.process(user)
            
            user.enter(self.env.now)
            yield self.IS_input.process(user)
            yield self.FIFO_sequential.process(user)
            yield self.IS_between_servers.process(user)

            download_time = (file_size - full_segments_number * self.FIFO_segmented.segment_size) / user.mean_download_speed
            yield self.FIFO_segmented.process(user, download_time)
            yield self.IS_output.process(user)
            user.out(self.env.now)

        else:
            user.enter(self.env.now)
            yield self.IS_input.process(user)
            yield self.FIFO_sequential.process(user)
            yield self.IS_between_servers.process(user)

            download_time = file_size / user.mean_download_speed
            yield self.FIFO.process(user, download_time)
            yield self.IS_output.process(user)
            user.out(self.env.now)

        self.register_time(user, self.env.now, False)
    
    def gen_users(self):
        while True:
            yield self.env.timeout(np.random.exponential(self.avg_arrival_time))
            user = self.create_user()
            self.users.put(user)
            self.env.process(self.flow(user))

    def run(self):
        self.env.process(self.gen_users())
        self.env.run(until=self.time)


def plot_queue_and_service_data(system, end_time):  
    if not system.net_data:
        print("Brak danych do wyświetlenia wykresów.")
        return

    net_data = defaultdict(lambda: defaultdict(list))
    
    times, users, is_entrances = zip(*system.net_data.queue)
    
    types = ('standard', 'premium', 'VIP', 'all')
    
    for type in types:
        net_data[type]['in_net_numbers'] = [0]
    for time, user, is_entrance in zip(times, users, is_entrances):
        net_data[user.type]['times'].append(time)
        net_data[user.type]['in_net_numbers'].append(net_data[user.type]['in_net_numbers'][-1] + (1 if is_entrance else -1))
        net_data['all']['in_net_numbers'].append(net_data['all']['in_net_numbers'][-1] + (1 if is_entrance else -1))
    net_data['all']['times'] = times
    
    fig, axs = plt.subplots(4, 1, figsize=(8, 6), sharex=True)
    
    for i, type in enumerate(types):
        axs[i].stairs(net_data[type]['in_net_numbers'], [0] + list(net_data[type]['times']) + [end_time], fill=True, color='green', label=type)
        axs[i].set_xlabel('Time')
        axs[i].set_ylabel('Users in net')
        axs[i].set_title(f"Number of users in net over time - {type}")
        axs[i].legend()
        max_in_service = max(net_data[type]['in_net_numbers']) if net_data[type]['in_net_numbers'] else 1
        axs[i].set_ylim(0, max_in_service + 1)
        axs[i].set_xlim(0, end_time)
        axs[i].grid(True)
    
    fig.tight_layout()
    fig.show()
    
    print('Mean times:')
    for resource, resource_str in system.resources:
        print(f'\t{resource_str}')
        print(f'\t\tin system: {np.mean([tup[0] for tup in resource.times_in_system.queue])}')
        print(f'\t\tin service: {np.mean([tup[0] for tup in resource.times_in_service.queue])}')
        print(f'\t\tin queue: {np.mean([tup[0] for tup in resource.times_in_queue.queue])}')
        queue_data = defaultdict(list)
        in_service_data = defaultdict(list)
        resource_queue_data = resource.queue_data.queue
        resource_in_service_data = resource.in_service_data.queue
        
        for tup1, tup2 in zip(resource_queue_data, resource_in_service_data):
            queue_data['times'].append(tup1[0])
            queue_data['data'].append(tup1[2])
            in_service_data['times'].append(tup2[0])
            in_service_data['data'].append(tup2[2])
            
        fig, axs = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        
        for i, q_data in enumerate((queue_data, in_service_data)):
            axs[i].stairs(q_data['data'], q_data['times'] + [end_time], fill=True, color='green' if i else 'blue', label='service' if i else 'queue')
            axs[i].set_xlabel('Time')
            axs[i].set_ylabel('Users')
            axs[i].set_title(f"Number of users in {'service' if i else 'queue'} in {resource_str}")
            axs[i].legend()
            max_in_service = max(q_data['data']) if q_data['data'] else 1
            axs[i].set_ylim(0, max_in_service + 1)
            axs[i].set_xlim(0, end_time)
            axs[i].grid(True)
        
        fig.tight_layout()
        fig.show()

def calculate_statistics(system: Resource, end_time):
    service_times = defaultdict(list)
    service_times_with_segmented = defaultdict(list)

    for user in system.users.queue:
        enter_time_len = len(user.enter_time)
        times = 0
        for i in range(len(user.enter_time) - 1):
            times += user.out_time[i] - user.enter_time[i]
        if enter_time_len == len(user.out_time):
            times += user.out_time[-1] - user.enter_time[-1]
            service_times_with_segmented[user.type].append(user.out_time[-1] - user.enter_time[0])
        else:
            times += end_time - user.enter_time[-1]
            service_times_with_segmented[user.type].append(end_time - user.enter_time[0])
        service_times[user.type].append(times)

    avg_service_time = {}
    avg_service_time_with_segmented = {}
    for type in ('standard', 'premium', 'VIP'):
        avg_service_time[type] = np.mean(service_times[type]) if service_times[type] else 0
        avg_service_time_with_segmented[type] = np.mean(service_times_with_segmented[type]) if service_times_with_segmented[type] else 0
    
    print("Wyniki:\n")
    print(f"Średni czas w systemie:")
    for key, val in avg_service_time_with_segmented.items():
        print(f"\t{key}: {val}")
    print(f"Średni czas w systemie (nie uwzględniając czasu spędzonego w IS_segmented):")
    for key, val in avg_service_time.items():
        print(f"\t{key}: {val}")
    print('')

def main():
    config = load_file('config_net.yaml')
    
    net = Net(config=config)
    net.run()
    
    end_time = config['simulation']['time']
    calculate_statistics(net, end_time=end_time)
    plot_queue_and_service_data(net, end_time=end_time)

    plt.show()


if __name__ == '__main__':
    main()
