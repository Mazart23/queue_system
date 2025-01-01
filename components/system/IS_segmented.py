import simpy

from . import Resource
from ..users import User


class IS_segmented(Resource):
    def __init__(self, env: simpy.Environment, config: dict):
        super().__init__(env, config)
        self.segment_watchtime = self.config['segment_watchtime']
        self.earlier_download = self.config['earlier_download']
        self.users_time = {}

    def process(self, user: User):
        def _process_logic():
            enter_time = self.env.now
            self.track_queue_length_and_service(enter_time, user)
            time_to_wait = self.segment_watchtime - min(enter_time - self.users_time.get(user.id, enter_time), self.earlier_download)
            
            with self.resource.request() as request:
                yield request
                process_time = self.env.now
                self.track_queue_length_and_service(process_time, user)
                
                yield self.env.timeout(time_to_wait)
                out_time = self.env.now
                self.track_queue_length_and_service(out_time, user)
                self.users_time[user.id] = out_time

            self.time_in_queue(user, process_time, enter_time)
            self.time_in_service(user, out_time, process_time)
            self.time_in_system(user, out_time, enter_time)
        return self.env.process(_process_logic())