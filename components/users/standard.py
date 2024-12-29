from . import User


class UserStandard(User):

    counter = 0

    def __init__(self, config: dict):
        super().__init__(config)
        self.__class__.counter += 1
        self.type = 'standard'
