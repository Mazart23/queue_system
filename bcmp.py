from queue import Queue
import math

import yaml
import simpy
import numpy as np
import matplotlib.pyplot as plt

from .components.system import Resource
from .components.system.IS import IS
from .components.system.IS_segmented import IS_segmented
from .components.system.FIFO import FIFO
from .components.system.FIFO_segmented import FIFO_segmented
from .components.system.FIFO_sequential import FIFO_sequential
from .components.users import User
from .components.users.standard import UserStandard
from .components.users.premium import UserPremium
from .components.users.vip import UserVIP


def load_file(filename):
    with open(filename, 'r') as file:
        return yaml.safe_load(file)


def create_user(wages):
    user_types = [
        UserStandard,
        UserPremium,
        UserVIP,
    ]
    user = np.random.choice(user_types, 1, p=wages)()
    return user


class Net:
    
    def __init__(self, config: dict) -> None:
        self.time = config['time']
        self.users = Queue()
        self.net_data = Queue()  # czasy użytkowników
        self.in_net = 0 # liczba użytkowników w sieci

        self.env = simpy.Environment()
        self.IS_input = IS(self.env, config['IS_input'])
        self.FIFO_sequential = FIFO_sequential(self.env, config['FIFO_sequential'])
        self.IS_between_servers = IS(self.env, config['IS_between_servers'])
        self.FIFO = FIFO(self.env, config['FIFO'])
        self.FIFO_segmented = FIFO_segmented(self.env, config['IS_between_servers'])
        self.IS_segmented = IS_segmented(self.env, config['IS_segmented'])
        self.IS_output = IS(self.env, config['IS_output'])
        self.service = simpy.Resource(self.env, capacity=config['number_of_servers'])

    def register_time(self, user: User, time: float, is_entrance: bool):
        self.in_net += 1 if is_entrance else -1
        self.net_data.put((time, user, self.in_net))

    def flow(self, user: User):
        self.register_time(user, self.env.now, True)
        file_size = abs(np.random.normal(user.mean_file_size))

        if isinstance(user, UserVIP):       
            full_segments_number = math.floor(file_size / self.segment_size)
            segments = [self.segment_size for _ in range(full_segments_number)]

            for segment in segments:
                self.IS_input.process(user)
                self.FIFO_sequential.process(user)
                self.IS_between_servers.process(user)

                download_time = segment / self.mean_download_speed
                self.FIFO_segmented.process(user, download_time)
                self.IS_output.process(user)
                self.IS_segmented(user)
            
            self.IS_input.process(user)
            self.FIFO_sequential.process(user)
            self.IS_between_servers.process(user)

            download_time = (file_size - full_segments_number * self.segment_size) / self.mean_download_speed
            self.FIFO_segmented.process(user, download_time)
            self.IS_output.process(user)

        else:
            self.IS_input.process(user)
            self.FIFO_sequential.process(user)
            self.IS_between_servers.process(user)

            download_time = file_size / self.mean_download_speed
            self.FIFO.process(user, download_time)
            self.IS_output.process(user)

        self.register_time(user, self.env.now, False)
    
    def gen_users(self):
        while True:
            yield self.env.timeout(np.random.exponential(self.avg_arrival_time))
            user = create_user(wages=(0.5, 0.3, 0.2))
            self.users.put(user)
            self.env.process(self.flow(user))

    def run(self):
        self.env.process(self.gen_users())
        self.env.run(until=self.time)


def plot_queue_and_service_data(system, end_time):  
    if not system.queue_data or not system.in_service_data:
        print("Brak danych do wyświetlenia wykresów.")
        return

    times_queue, queue_lengths = zip(*system.queue_data)
    times_service, in_service_lengths = zip(*system.in_service_data)

    fig, axs = plt.subplots(2, 1, figsize=(8, 6), sharex=True)

    # Pierwszy wykres - liczba użytkowników w kolejce
    axs[0].stairs(queue_lengths, list(times_queue) + [end_time], fill=True, color='blue', label='Users in Queue')
    axs[0].set_ylabel('Users in Queue')
    axs[0].set_title(f"Queue Length Over Time - {'Segmented' if system.is_segmented else 'Non-Segmented'}")
    axs[0].legend()
    axs[0].set_ylim(0, max(queue_lengths) + 1)
    axs[0].set_xlim(0, end_time)
    axs[0].grid(True)

    # Drugi wykres - liczba obsługiwanych użytkowników
    axs[1].stairs(in_service_lengths, list(times_service) + [end_time], fill=True, color='green', label='Users in Service')
    axs[1].set_xlabel('Time')
    axs[1].set_ylabel('Users in Service')
    axs[1].set_title("Number of Users in Service Over Time")
    axs[1].legend()
    max_in_service = max(in_service_lengths) if in_service_lengths else 1
    axs[1].set_ylim(0, max_in_service + 1)  # Dodano margines dla osi Y, aby uwzględnić pełen zakres
    axs[1].set_xlim(0, end_time)
    axs[1].grid(True)

    fig.tight_layout()
    fig.show()


def calculate_statistics(system: Resource, end_time):
    queue_times = []
    service_times = []
    for user in system.users.queue:
        enter_time_len = len(user.enter_time)
        for i in range(len(user.enter_time) - 1):
            queue_times.append(user.process_time[i] - user.enter_time[i])
            service_times.append(user.out_time[i] - user.process_time[i])
        if enter_time_len == len(user.process_time):
            queue_times.append(user.process_time[-1] - user.enter_time[-1])
            if enter_time_len == len(user.out_time):
                service_times.append(user.out_time[-1] - user.process_time[-1])
            else:
                service_times.append(end_time - user.process_time[-1])
        else:
            queue_times.append(end_time - user.enter_time[-1])
    
    avg_waiting_time = np.mean(queue_times) if queue_times else 0
    avg_service_time = np.mean(service_times) if service_times else 0
    print("Wyniki:")
    print(f"Średni czas oczekiwania w kolejce: {avg_waiting_time}")
    print(f"Średni czas obsługi użytkownika: {avg_service_time}")

def calculate_statistics(system: Resource, end_time):
    queue_times = []
    service_times = []
    for user in system.users.queue:
        enter_time_len = len(user.enter_time)
        for i in range(len(user.enter_time) - 1):
            queue_times.append(user.process_time[i] - user.enter_time[i])
            service_times.append(user.out_time[i] - user.process_time[i])
        if enter_time_len == len(user.process_time):
            queue_times.append(user.process_time[-1] - user.enter_time[-1])
            if enter_time_len == len(user.out_time):
                service_times.append(user.out_time[-1] - user.process_time[-1])
            else:
                service_times.append(end_time - user.process_time[-1])
        else:
            queue_times.append(end_time - user.enter_time[-1])
    
    avg_waiting_time = np.mean(queue_times) if queue_times else 0
    avg_service_time = np.mean(service_times) if service_times else 0
    print("Wyniki:")
    print(f"Średni czas oczekiwania w kolejce: {avg_waiting_time}")
    print(f"Średni czas obsługi użytkownika: {avg_service_time}")

def main():
    config = load_file('config_net.yaml')
    
    net = Net(config=config)
    net.run()
    
    # Wyświetl statystyki przed wykresem
    # end_time = config['time']
    # calculate_statistics(net, end_time=end_time)
    # plot_queue_and_service_data(net, end_time=end_time)

    # plt.show()


if __name__ == '__main__':
    main()
