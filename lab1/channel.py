import queue
import random

class MsgQueue:
    def __init__(self, loss_probability=0.0, name="channel"):
        """
        loss_probability: вероятность потери пакета (0.0 – 1.0)
        name: имя канала для отладки
        """
        self.queue = queue.Queue()
        self.loss_probability = loss_probability
        self.name = name
        self.total_put = 0
        self.total_lost = 0

    def put(self, packet):
        """Попытаться положить пакет в очередь. С вероятностью loss_probability пакет теряется."""
        self.total_put += 1
        if random.random() < self.loss_probability:
            self.total_lost += 1
            return False
        self.queue.put(packet)
        return True

    def get(self, timeout=None):
        """Извлечь пакет из очереди. Если очередь пуста и timeout=None, блокируется до появления пакета."""
        return self.queue.get(timeout=timeout)

    def get_nowait(self):
        """Неблокирующее извлечение. Если очередь пуста — бросает queue.Empty."""
        return self.queue.get_nowait()

    def empty(self):
        return self.queue.empty()

    def qsize(self):
        return self.queue.qsize()

    def __repr__(self):
        return f"MsgQueue(name={self.name}, loss_prob={self.loss_probability})"