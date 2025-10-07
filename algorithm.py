#!/usr/bin/env python3
from typing import List
import time
from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction, SimulationEvent
from GUI import GUI
from utils import Message

class ElevatorBusExampleController(ElevatorController):
    def __init__(self, start_event, finish_event, message_queue) -> None:
        super().__init__("http://127.0.0.1:8000", True)
        self.all_passengers: List[ProxyPassenger] = []
        self.max_floor = 0

        #用于与GUI进程进行通信的同步变量和消息队列
        self.start_event = start_event
        self.finish_event = finish_event    
        self.message_queue = message_queue

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        self.max_floor = floors[-1].floor
        self.floors = floors
        for i, elevator in enumerate(elevators):
            # 计算目标楼层 - 均匀分布在不同楼层
            target_floor = (i * (len(floors) - 1)) // len(elevators)
            # 立刻移动到目标位置并开始循环
            elevator.go_to_floor(target_floor, immediate=True)
        print("-----------------------------------")
        print('begin initialization')
        for e in elevators:
            print(f'{e.id} floor:{e.current_floor_float}')
        print("---------------------------------")
        #初始化阶段实例化初始化了数部电梯,在这里我们将电梯的初始化事件加入到message queue当中
        #默认电梯都在0层???为什么这里是从第0层开始的.需要确认一下电梯是不是都在第0层被初始化
        for e in elevators:
            new_message = Message(type = 'init', object= 'elevator', id = e.id, floor = e.current_floor, state = None)
            self.message_queue.put(new_message)

        pass

    def on_event_execute_start(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        print(f"Tick {tick}: 即将处理 {len(events)} 个事件 {[e.type.value for e in events]}")
        for i in elevators:
            print(
                f"\t{i.id}[{i.target_floor_direction.value},{i.current_floor_float}/{i.target_floor}]"
                + "👦" * len(i.passengers),
                end="",
            )
        print()

    def on_event_execute_end(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        print(f"Tick {tick}: 处理了 {len(events)} 个事件 {[e.type.value for e in events]}")
        for i in elevators:
            print(
                f"\t{i.id}[{i.target_floor_direction.value},{i.current_floor_float}/{i.target_floor}]"
                + "👦" * len(i.passengers),
                end="",
            )
            print(i.passengers)
        for e in events:
            print(e.type)
        print()
        #time.sleep(1)
        #在每一个tick处理完毕之后，我们需要通知GUI进程进行更新，然后等待GUI完成更新
        #首先处理电梯的信息,不管是否处在stopped状态，都为它创建一个更新事件
        for e in elevators:
            new_message = Message(type = 'elevator', object= None, id = e.id, floor = e.current_floor_float, state = 0)
            self.message_queue.put(new_message)
            #为电梯中的每个用户创建事件
            for p in e.passengers:
                new_message = Message(type = 'passenger', object= None, id = p, floor = e.current_floor_float, state = -2)
                self.message_queue.put(new_message)
        #处理用户初始化，登上电梯以及离开电梯的事件
        for e in events:
            #乘客的初始化事件
            if e.type.value == 'down_button_pressed':
                new_message = Message(type = 'init', object= 'passenger', id = e.data['passenger'], floor = e.data['floor'], state = None)
                self.message_queue.put(new_message)
            #乘客登上电梯事件
            elif e.type.value == 'passenger_board':
                print('------passenger board----------:')
                print(f'{e.data['passenger']} floor = {e.data['floor']}, state = {e.data['elevator']}')
                new_message = Message(type = 'passenger', object= None, id = e.data['passenger'], floor = e.data['floor'], state = e.data['elevator'])
                self.message_queue.put(new_message)
            #乘客离开电梯事件，注意，由于模拟器把停靠和离开放在同一tick里，因此这里是delay事件
            elif e.type.value == 'passenger_alight':
                new_message = Message(type = 'passenger', object= 'passenger', id = e.data['passenger'], floor = e.data['floor'], state = -1, delay = True)
                self.message_queue.put(new_message)
        #消息已经准备好了，通知GUI进程可以进行更新
        self.start_event.set()
        # #等待GUI进程完成更新，这里的wait必须后面跟着一个clear，否则无法生效
        self.finish_event.wait()
        self.finish_event.clear()

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        print(f"📞 乘客 P{passenger.id} 在 F{floor.floor} 呼叫电梯 {direction}")
        self.all_passengers.append(passenger)
        
        pass

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        elevator.go_to_floor(1)

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        print(f"🛑 电梯 E{elevator.id} 停靠在 F{floor.floor}")
        # BUS调度算法，电梯到达顶层后，立即下降一层
        if elevator.last_tick_direction == Direction.UP and elevator.current_floor == self.max_floor:
            elevator.go_to_floor(elevator.current_floor - 1)
        # 电梯到达底层后，立即上升一层
        elif elevator.last_tick_direction == Direction.DOWN and elevator.current_floor == 0:
            elevator.go_to_floor(elevator.current_floor + 1)
        elif elevator.last_tick_direction == Direction.UP:
            elevator.go_to_floor(elevator.current_floor + 1)
        elif elevator.last_tick_direction == Direction.DOWN:
            elevator.go_to_floor(elevator.current_floor - 1)

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        print(f"👦 乘客 P{passenger.id} 进入电梯 E{elevator.id}")

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        print(f"👦 乘客 P{passenger.id} 离开电梯 E{elevator.id} 在 F{floor.floor}")

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        pass

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        pass


def Start_Algorithm(start_event, finish_event, message_queue):
    algorithm = ElevatorBusExampleController(start_event, finish_event, message_queue)
    algorithm.start()

# Start_Algorithm(None,None,None)