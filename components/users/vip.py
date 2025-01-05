from . import User


class UserVIP(User):

    counter = 0

    def __init__(self, config: dict):
        super().__init__(config)
        self.__class__.counter += 1
        self.type = 'VIP'
        self.wait_time = []

    def track_wait_time(self, time) -> None:
        self.wait_time.append(time)