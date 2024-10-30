from typing import Dict
from queue import Queue
import math
import yaml
import simpy
import numpy as np
import matplotlib.pyplot as plt  

def load_file(filename):
    with open(filename, 'r') as file:
        return yaml.safe_load(file)

class QueueSystem:
    
    def __init__(self, config: Dict[str, int], env: simpy.core.Environment, service: simpy.resources.resource.Resource) -> None:
        self.time = config['time']
        self.avg_arrival_time = config['avg_arrival_time']
        self.mean_file_size = config['mean_file_size']
        self.mean_download_speed = config['mean_download_speed']
        self.segment_size = config['segment_size']
        self.segment_watchtime = config['segment_watchtime']
        self.is_segmented = config['is_segmented']
        self.users = Queue()
        self.queue_data = []  # Lista do przechowywania danych o długości kolejki
        self.in_service_data = []  # Lista do przechowywania danych o liczbie obsługiwanych użytkowników
        self.waiting_times = []  # Lista do przechowywania czasów oczekiwania użytkowników
        self.service_times = []  # Lista do przechowywania czasów obsługi użytkowników

        self.env = env
        self.service = service

    class User:

        counter = 0
        
        def __init__(self) -> None:
            self.__class__.counter += 1
            self.id = self.__class__.counter
            self.enter_time = None
            self.start_service_time = None
            self.end_service_time = None
            self.segments = 1

        def __str__(self):
            return f'User {self.id}'
        
        def enter(self, time, segment_number=0) -> None:
            self.enter_time = time
            print(f'{self} przychodzi w czasie {time}, segment {segment_number + 1} / {self.segments}')

        def process(self, time, segment_number=0) -> None:
            self.start_service_time = time
            print(f'{self} jest obsługiwany w czasie {time}, segment {segment_number + 1} / {self.segments}')

        def out(self, time, segment_number=0) -> None:
            self.end_service_time = time
            print(f'{self} zakończył obsługę w czasie {time}, segment {segment_number + 1} / {self.segments}')

    def track_queue_length_and_service(self, time):
        queue_length = len(self.service.queue)  # Liczba użytkowników w kolejce
        in_service = self.service.count  # Liczba użytkowników aktualnie obsługiwanych
        self.queue_data.append((time, queue_length))
        self.in_service_data.append((time, in_service))

    def user_process(self, user: User):
        user.enter(self.env.now)
        self.track_queue_length_and_service(self.env.now)  # Rejestracja po przyjściu
        
        file_size = abs(np.random.normal(self.mean_file_size))
        download_time = file_size / self.mean_download_speed

        with self.service.request() as request:
            yield request
            user.process(self.env.now)
            self.track_queue_length_and_service(self.env.now)  # Rejestracja po rozpoczęciu obsługi
            
            yield self.env.timeout(download_time)
            user.out(self.env.now)
            self.track_queue_length_and_service(self.env.now)  # Rejestracja po zakończeniu obsługi

        # Obliczenie czasu oczekiwania i obsługi dla użytkownika
        if user.enter_time is not None and user.start_service_time is not None and user.end_service_time is not None:
            waiting_time = user.start_service_time - user.enter_time
            service_time = user.end_service_time - user.start_service_time
            self.waiting_times.append(waiting_time)
            self.service_times.append(service_time)

    def user_process_segmented(self, user: User):     
        file_size = abs(np.random.normal(self.mean_file_size))
        
        full_segments_number = math.floor(file_size / self.segment_size)
        segments = [self.segment_size for _ in range(full_segments_number)]
        segments.append(file_size - full_segments_number * self.segment_size)
        user.segments = len(segments)
        
        for i, segment in enumerate(segments):
            user.enter(self.env.now, i)
            self.track_queue_length_and_service(self.env.now)  # Rejestracja po przyjściu
            
            download_time = segment / self.mean_download_speed
            with self.service.request() as request:
                yield request
                user.process(self.env.now, i)
                self.track_queue_length_and_service(self.env.now)  # Rejestracja po rozpoczęciu obsługi
                
                yield self.env.timeout(download_time)
                user.out(self.env.now, i)
                self.track_queue_length_and_service(self.env.now)  # Rejestracja po zakończeniu obsługi
            yield self.env.timeout(self.segment_watchtime)

        # Obliczenie czasu oczekiwania i obsługi dla użytkownika
        if user.enter_time is not None and user.start_service_time is not None and user.end_service_time is not None:
            waiting_time = user.start_service_time - user.enter_time
            service_time = user.end_service_time - user.start_service_time
            self.waiting_times.append(waiting_time)
            self.service_times.append(service_time)
    
    def gen_users(self):
        while True:
            yield self.env.timeout(np.random.exponential(self.avg_arrival_time))
            user = self.User()
            self.users.put(user)
            self.env.process(self.user_process_segmented(user) if self.is_segmented else self.user_process(user))

    def run(self):
        self.env.process(self.gen_users())
        self.env.run(until=self.time)

    def plot_queue_and_service_data(self):  
        if not self.queue_data or not self.in_service_data:
            print("Brak danych do wyświetlenia wykresów.")
            return

        times, queue_lengths = zip(*self.queue_data)
        _, in_service_lengths = zip(*self.in_service_data)
        
        # Ustawienia rozmiaru wykresu
        fig, axs = plt.subplots(2, 1, figsize=(8, 6), sharex=True)

        # Pierwszy wykres - liczba użytkowników w kolejce
        axs[0].bar(times, queue_lengths, width=0.5, color='blue', label='Users in Queue')
        axs[0].set_ylabel('Users in Queue')
        axs[0].set_title(f"Queue Length Over Time - {'Segmented' if self.is_segmented else 'Non-Segmented'}")
        axs[0].legend()
        axs[0].set_ylim(0, max(queue_lengths) + 1)

        # Drugi wykres - liczba obsługiwanych użytkowników
        axs[1].bar(times, in_service_lengths, width=0.5, color='green', label='Users in Service')
        axs[1].set_xlabel('Time')
        axs[1].set_ylabel('Users in Service')
        axs[1].set_title("Number of Users in Service Over Time")  # Tytuł dla drugiego wykresu
        axs[1].legend()
        max_in_service = max(in_service_lengths) if in_service_lengths else 1
        axs[1].set_ylim(0, max_in_service + 1)  # Dodano margines dla osi Y, aby uwzględnić pełen zakres

        plt.tight_layout()
        plt.show()

    def calculate_statistics(self):
        # Filtrowanie tylko pełnych czasów oczekiwania i obsługi
        completed_waiting_times = [wt for wt in self.waiting_times if wt is not None]
        completed_service_times = [st for st in self.service_times if st is not None]
        
        avg_waiting_time = np.mean(completed_waiting_times) if completed_waiting_times else 0
        avg_service_time = np.mean(completed_service_times) if completed_service_times else 0
        
        print(f"\nŚredni czas oczekiwania w kolejce: {avg_waiting_time:.2f}")
        print(f"Średni czas obsługi użytkownika: {avg_service_time:.2f}")

def main():
    config = load_file('config.yaml')
    
    env = simpy.Environment()
    service = simpy.Resource(env, capacity=config['number_of_servers'])
    
    system = QueueSystem(config, env, service)
    system.run()
    
    # Wyświetl statystyki przed wykresem
    system.calculate_statistics()
    system.plot_queue_and_service_data()  # Wyświetlenie wykresu na końcu

if __name__ == '__main__':
    main()

