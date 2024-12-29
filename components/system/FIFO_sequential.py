import numpy as np

from . import Resource
from ..users import User


class FIFO_sequential(Resource):
    def __init__(self):
        super().__init__()
        self.time = self.config['time']
        self.number_of_channels = self.config['number_of_channels']
    
    def process(self, user: User):
        enter_time = self.env.now
        user.enter(enter_time)
        self.track_queue_length_and_service(enter_time)

        with self.resource.request() as request:
            yield request
            process_time = self.env.now
            user.process(process_time)
            self.track_queue_length_and_service(process_time)
            
            yield self.env.timeout(self.time)
            out_time = self.env.now
            user.out(out_time)
            self.track_queue_length_and_service(out_time)