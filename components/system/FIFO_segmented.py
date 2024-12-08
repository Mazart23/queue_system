import numpy as np

from .import System
from ..users import User


class FIFO_segmented(System):
    def __init__(self):
        super().__init__()
        self.segment_size = self.config['segment_size']
    
    def process(self, user: User):
        enter_time = self.env.now
        user.enter(enter_time)
        self.track_queue_length_and_service(enter_time)
        
        file_size = abs(np.random.normal(user.mean_file_size))
        download_time = file_size / self.mean_download_speed

        with self.resource.request() as request:
            yield request
            process_time = self.env.now
            user.process(process_time)
            self.track_queue_length_and_service(process_time)
            
            yield self.env.timeout(download_time)
            out_time = self.env.now
            user.out(out_time)
            self.track_queue_length_and_service(out_time)
        