from . import User


class UserStandard(User):

    counter = 0

    def __init__(self) -> None:
        super().__init__()
        self.__class__.counter += 1
