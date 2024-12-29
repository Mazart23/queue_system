import numpy as np
import simpy

from . import Resource
from ..users import User


class FIFO_segmented(Resource):
    def __init__(self, env: simpy.Environment, config: dict):
        super().__init__(env, config)
        self.segment_size = self.config['segment_size']
    
    def process(self, user: User, time):
        def _process_logic():
            enter_time = self.env.now
            self.track_queue_length_and_service(enter_time, user)

            with self.resource.request() as request:
                yield request
                process_time = self.env.now
                self.track_queue_length_and_service(process_time, user)
                
                yield self.env.timeout(time)
                out_time = self.env.now
                self.track_queue_length_and_service(out_time, user)
            
            self.time_in_queue(user, process_time, enter_time)
            self.time_in_service(user, out_time, process_time)
            self.time_in_system(user, out_time, enter_time)
        return self.env.process(_process_logic())
        