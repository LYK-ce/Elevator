from algorithm import Start_Algorithm
from GUI import GUI
from multiprocessing import Process, Event, Queue

if __name__ == "__main__":
    #定义两个线程之间的同步变量
    start_event = Event()
    finish_event = Event()
    message_queue = Queue()

    algorithm = Process(target=Start_Algorithm, args=(start_event, finish_event, message_queue))
    gui = Process(target=GUI,args=(start_event, finish_event, message_queue))
    algorithm.start()
    gui.start() 

    algorithm.join()