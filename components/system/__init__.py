from abc import ABC
from queue import Queue

import simpy

from ..users import User


class Resource(ABC):

    def __init__(self, env: simpy.Environment, config: dict):
        '''
        If number of servers is not specified then create infinite capacity
        '''
        self.env = env
        self.resource = simpy.Resource(env, capacity=config['number_of_servers']) \
            if 'number_of_servers' in config \
            else simpy.Resource(env)
        self.config = config
        self.queue_data = Queue() # amount of users in queue
        self.in_service_data = Queue() # amount of users in system
        self.time_in_service = Queue() # time spended in system for single request

    
    def track_queue_length_and_service(self, time):
        queue_length = len(self.service.queue)
        in_service = self.service.count
        self.queue_data.put((time, queue_length))
        self.in_service_data.put((time, in_service))
    
    def time_in_system(self, user: User, out_time: float, in_time: float):
        self.time_in_service.put((out_time - in_time, user.__class__))