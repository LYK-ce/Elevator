'''
使用 Pygame 创建一个简单的电梯调度算法可视化界面
实现以下基本功能：
1. 显示电梯和楼层
2. 快速更新/播放动画更新
3. 电梯与乘客全部设置成class，并提供update方法，在主循环当中统一调用所有对象的update方法
'''
import pygame
import sys
from multiprocessing import Event, Queue
import random
from utils import Message
import time
#定义常量
WAITING = 100
WAITING_RANDOM = 100
ELEVATOR_X = [275, 425, 575, 725]
ELEVATOR_RANDOM = 24
DESTROY = 900
FLOOR_HEIGHT = 150
MAX_FRAME = 30
RATE = 1

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 1000

#楼层到y坐标的转换函数，记住，楼层是从第0层开始的。
def Floor_To_Y(floor):
    return 950 - (floor) * FLOOR_HEIGHT


# 设置颜色
GRAY = (200, 200, 200)

# 定义电梯类
class Elevator(pygame.sprite.Sprite):
    #输入的x和y是电梯锚点的位置，锚点位于image的bottom center位置上
    def __init__(self, x, y, _image_path = None, _id = None):
        super().__init__()
        self.image = pygame.image.load(_image_path) 
        self.id = _id
        #定义sprite的锚点
        self.anchor = [x, y]
        self.rect = self.image.get_rect()
        self.rect.x = self.anchor[0] - self.rect.width // 2
        self.rect.y = self.anchor[1] - self.rect.height

        self.target = (x, y)
    
    def Rect_To_Anchor(self):
        self.anchor = (self.rect.x + self.rect.width // 2, self.rect.y + self.rect.height)
        return self.anchor
    def Anchor_To_Rect(self):
        self.rect.x = self.anchor[0] - self.rect.width // 2
        self.rect.y = self.anchor[1] - self.rect.height
        return self.rect

    def update(self, frame):
        #根据anchor和target之间的距离，计算相对位置
        self.anchor[0] = self.anchor[0] + (self.target[0] - self.anchor[0]) * frame / (MAX_FRAME * RATE)
        self.anchor[1] = self.anchor[1] + (self.target[1] - self.anchor[1]) * frame / (MAX_FRAME * RATE)
        self.Anchor_To_Rect()
        

# 定义乘客类
class Person(pygame.sprite.Sprite):
    def __init__(self, x, y, _image_path, _id = None):
        super().__init__()
        self.image = pygame.image.load(_image_path) 
        self.id = _id
        #定义sprite的锚点
        self.anchor = [x, y]
        self.rect = self.image.get_rect()
        self.rect.x = self.anchor[0] - self.rect.width // 2
        self.rect.y = self.anchor[1] - self.rect.height

        self.target = (x, y)
    
    def Rect_To_Anchor(self):
        self.anchor = (self.rect.x + self.rect.width // 2, self.rect.y + self.rect.height)
        return self.anchor
    def Anchor_To_Rect(self):
        self.rect.x = self.anchor[0] - self.rect.width // 2
        self.rect.y = self.anchor[1] - self.rect.height
        return self.rect
    
    def update(self, frame):
        if self.anchor[0] == DESTROY:
            return
        #根据anchor和target之间的距离，计算相对位置
        self.anchor[0] = self.anchor[0] + (self.target[0] - self.anchor[0]) * frame / (MAX_FRAME * RATE)
        self.anchor[1] = self.anchor[1] + (self.target[1] - self.anchor[1]) * frame / (MAX_FRAME * RATE)
        self.Anchor_To_Rect()
        
            
   
 
def GUI(start_event, finish_event, message_queue):
    # 初始化 Pygame
    pygame.init()

    # 设置窗口大小
    screen_width, screen_height = 1000, 1000
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("电梯调度算法可视化")


    # 创建电梯和乘客的精灵组
    elevators = pygame.sprite.Group()
    passengers = pygame.sprite.Group()

    elevator_num = 0

    #处理特殊情况使用的队列
    delayed_queue = Queue()
    delayed_process = False


    # 主循环
    running = True
    updateing = False
    clock = pygame.time.Clock()
    frame = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        #必须等到调度算法的一个tick完成之后，同时不处在更新状态时才能进行下一次更新
        if start_event.is_set() and not updateing:
        # if not updateing:
            # print(f'updating current time',time.perf_counter())
            #根据message_queue中的信息，更新电梯和乘客的target位置
            while not message_queue.empty():
                message = message_queue.get()
                if message.delay == True:
                #如果出现了delay的message，表示此消息要暂缓一个tick执行，放在下一个tick执行，因此先将其暂存到delaye queue当中。
                    message.delay = False
                    delayed_queue.put(message)
                    delayed_process = True
                else:
                #消息分为三类，实例化消息，电梯消息和乘客消息
                #对于实例化消息，根据传入的类型，创建相应的电梯和乘客对象
                #对于电梯消息，更新电梯位置
                #对于乘客消息，更新电梯位置，需要注意的是，位于电梯中的乘客随电梯上升或者下降位置也需要设置成事件发送过来
                    if message.type == 'init':
                        if message.object== 'elevator':
                            new_elevator = Elevator(ELEVATOR_X[elevator_num], Floor_To_Y(message.floor), 'Sprite\elevator.png')
                            new_elevator.id = message.id
                            print("创建电梯对象：", new_elevator)
                            elevators.add(new_elevator)
                            elevator_num += 1

                        elif message.object== 'passenger':
                            #在waiting位置上随机偏移一个位置生成对应的角色
                            #先创建在camera外面，然后走进视野内
                            new_person = Person(-100, Floor_To_Y(message.floor), 'Sprite\passenger01.png')
                            new_person.target = (WAITING + random.randint(-WAITING_RANDOM,WAITING_RANDOM), Floor_To_Y(message.floor))
                            new_person.id = message.id
                            passengers.add(new_person)
                            

                    elif message.type == 'elevator':
                        elevator = elevators.sprites()[message.id]
                        elevator.target = (ELEVATOR_X[message.id], Floor_To_Y(message.floor))   

                    elif message.type == 'passenger':
                        #这里还需要处理一个特殊情况，因为离开电梯和电梯停在某一层是同一tick发生的，因此必须特殊处理，我真是艹了。
                        #处理的方式是先将这些事件收集起来，在本次tick不进行处理，本tick处理完后额外增加一个tick，再来处理这些乘客的离开。
                        
                        #10.7实际运行起来和预期的还是不一样，虽然停在一层的tick和上电梯的tick不是同一个tick，这也意味着当乘客上电梯时电梯已经离开了，就会出现乘客没有正确站在电梯的位置上的问题。真是遭不住啊。


                    
                        #电梯是从0开始编号的，乘客却是从1开始编号的，吐了
                        passenger = passengers.sprites()[message.id-1]
                        #视情况而定，passenger要去往哪里
                        #到达楼层，前往销毁位置处
                        if message.state == -1:
                            passenger.target = (DESTROY, passenger.anchor[1])
                        #站在电梯里，随电梯前往特定位置
                        elif message.state == -2:
                            passenger.target = (passenger.anchor[0], Floor_To_Y(message.floor))
                        #位于等待位置上，前往电梯里
                        else:
                            #这里最好再添加一个检查电梯id号是否存在的逻辑
                            passenger.target = (ELEVATOR_X[message.state]+random.randint(-ELEVATOR_RANDOM,ELEVATOR_RANDOM), passenger.anchor[1])  
                    else:
                        print("未知消息类型")
        
            updateing = True
            frame = 0
            
        
        if updateing:
            frame += 1
            # 更新电梯和乘客的状态
            elevators.update(frame)
            passengers.update(frame)

            #在60帧内完成动画更新工作，然后设置finish_event，通知algorithm进程继续执行
            if frame >= (MAX_FRAME * RATE):
                updateing = False
                #我们要这里考虑特殊情况，即是否需要补一个tick
                if delayed_process == True:
                    # print(f'delay current time',time.perf_counter())
                    #需要补一个tick，那我们就delayed queue中的内容全部补充道message queue当中。
                    delayed_process = False
                    while not delayed_queue.empty():
                        item = delayed_queue.get()
                        message_queue.put(item)
                    # print(f'delay1 current time',time.perf_counter())
                else:
                    #无特殊情况需要处理，通知调度算法继续即可
                    start_event.clear()
                    finish_event.set()
                    pass


        # 绘制背景
        screen.fill(GRAY)

        # 绘制电梯和乘客
        elevators.draw(screen)
        passengers.draw(screen)

        # 更新屏幕
        pygame.display.flip()

        # 控制帧率
        clock.tick(MAX_FRAME)

    pygame.quit()
    sys.exit()


# message_queue = Queue()
# message1 = Message(type = 'init', object= 'elevator', id = 0, floor = 3, state = None)
# message2 = Message(type = 'init', object= 'elevator', id = 1, floor = 2, state = None)
# message3 = Message(type = 'init', object= 'passenger', id = 0, floor = 2.5, state = None)
# message4 = Message(type = 'passenger', object= None, id = 0, floor = 3, state = -2)
# message5 = Message(type = 'init', object= 'passenger', id = 1, floor = 3, state = None)
# message6 = Message(type = 'passenger', object= 'passenger', id = 0, floor = 3, state = -1, delay = True)
# message7 = Message(type = 'passenger', object= 'passenger', id = 1, floor = 3, state = -1, delay = True)
# message_queue.put(message1)
# message_queue.put(message2)
# message_queue.put(message3)
# message_queue.put(message4)
# message_queue.put(message5)
# message_queue.put(message6)
# message_queue.put(message7)
# GUI(None, None, message_queue)