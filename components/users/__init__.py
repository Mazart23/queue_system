from abc import ABC


class User(ABC):

    counter_general = 0
    
    def __init__(self) -> None:
        self.__class__.counter_general += 1
        self.id = self.__class__.counter_general
        self.enter_time = []
        self.out_time = []

    def __str__(self) -> str:
        return f'User {self.id}'
    
    def enter(self, time) -> None:
        self.enter_time.append(time)
        print(f'{self} przychodzi do sieci w czasie {time}')

    def out(self, time) -> None:
        self.out_time.append(time)
        print(f'{self} wychodzi z sieci w czasie {time}')
