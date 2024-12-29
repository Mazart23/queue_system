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
        self.resource = simpy.Resource(env, capacity=config['number_of_channels']) \
            if 'number_of_channels' in config \
            else simpy.Resource(env, capacity=10**6)
        self.config = config
        self.queue_data = Queue() # amount of users in queue
        self.in_service_data = Queue() # amount of users in system
        self.times_in_system = Queue() # time spended in system for single request
        self.times_in_service = Queue() # time spended in service for single request
        self.times_in_queue = Queue() # time spended in queue for single request
    
    def track_queue_length_and_service(self, time, user):
        queue_length = len(self.resource.queue)
        in_service = self.resource.count
        self.queue_data.put((time, user, queue_length))
        self.in_service_data.put((time, user, in_service))
    
    def time_in_system(self, user: User, out_time: float, in_time: float):
        self.times_in_system.put((out_time - in_time, user))
    
    def time_in_queue(self, user: User, out_time: float, in_time: float):
        self.times_in_queue.put((out_time - in_time, user))
        
    def time_in_service(self, user: User, out_time: float, in_time: float):
        self.times_in_service.put((out_time - in_time, user))