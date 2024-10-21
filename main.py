from typing import Dict

import yaml
import simpy
import numpy as np


def load_file(filename):
    with open(filename, 'r') as file:
        return yaml.safe_load(file)


class User:

        counter = 0
        
        def __init__(self) -> None:
            counter += 1
            self.id = counter

        def __str__(self):
            print(f'User {self.id}')


class QueueSystem:
    
    def __init__(self, config: Dict[str, int], env: simpy.core.Environment, service: simpy.resources.resource.Resource) -> None:
        self.time = config['time']
        self.avg_session_time = config['avg_session_time']
        self.avg_arrival_time = config['avg_arrival_time']

        self.env = env
        self.service = service

    class User:

        counter = 0
        
        def __init__(self) -> None:
            self.__class__.counter += 1
            self.id = self.__class__.counter
            self.enter_time = 0
            self.process_time = 0
            self.out_time = 0

        def __str__(self):
            return f'User {self.id}'
        
        def enter(self, time) -> None:
            print(f'{self} przychodzi w czasie {time}')
            self.enter_time = time

        def process(self, time) -> None:
            print(f'{self} jest obsługiwany w czasie {time}')
            self.process_time = time

        def out(self, time) -> None:
            print(f'{self} zakończył obsługę w czasie {time}')
            self.out_time = time

    def user_process(self, user: User):
        user.enter(self.env.now)
        with self.service.request() as request:
            yield request
            user.process(self.env.now)
            session_time = np.random.exponential(self.avg_session_time)
            yield self.env.timeout(session_time)
            user.out(self.env.now)

    def gen_users(self):
        while True:
            yield self.env.timeout(np.random.exponential(self.avg_arrival_time))
            self.env.process(self.user_process(self.User()))

    def run(self):
        self.env.process(self.gen_users())
        self.env.run(until=self.time)


def main():
    config = load_file('config.yaml')
    
    env = simpy.Environment()
    service = simpy.Resource(env, capacity=config['number_of_servers'])
    
    system = QueueSystem(config, env, service)

    system.run()


if __name__ == '__main__':
    main()
