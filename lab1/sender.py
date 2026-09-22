import threading
import time
import queue
from packet import Packet


class Sender:
    def __init__(self, data_queue, ack_queue, protocol='GBN',
                 window_size=4, timeout=0.2, total_packets=100):
        self.data_queue = data_queue
        self.ack_queue = ack_queue
        self.protocol = protocol
        self.window_size = window_size
        self.timeout = timeout
        self.total_packets = total_packets

        self.base = 0
        self.next_seq_num = 0
        self.unacked = {}          # {seq_num: Packet}
        self.total_sent = 0        # все попытки передачи
        self.start_time = None
        self.end_time = None
        self.done_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        self.start_time = time.time()
        while not self.done_event.is_set():
            # 1. Отправка новых пакетов, если в окне есть место
            while (self.next_seq_num < self.base + self.window_size and
                   self.next_seq_num < self.total_packets):
                self._transmit(self.next_seq_num)
                self.next_seq_num += 1

            # 2. Обработка всех доступных ACK (неблокирующее чтение)
            while True:
                try:
                    ack = self.ack_queue.get_nowait()
                except queue.Empty:
                    break
                self._handle_ack(ack)

            # 3. Проверка тайм-аутов
            self._check_timeouts()

            # 4. Проверка завершения
            if self.base >= self.total_packets:
                self.end_time = time.time()
                self.done_event.set()
                break

            # Небольшая пауза, чтобы не нагружать процессор
            time.sleep(0.001)

    def _transmit(self, seq_num):
        """Отправить (или повторно отправить) пакет с заданным номером."""
        packet = Packet(seq_num=seq_num, data=f"data_{seq_num}")
        packet.send_time = time.time()
        self.unacked[seq_num] = packet
        self.data_queue.put(packet)
        self.total_sent += 1

    def _handle_ack(self, ack):
        if not ack.is_ack:
            return
        ack_num = ack.ack_num

        if self.protocol == 'GBN':
            # Накопленное подтверждение: все пакеты до ack_num включительно
            if ack_num >= self.base:
                for seq in [s for s in self.unacked if s <= ack_num]:
                    del self.unacked[seq]
                self.base = ack_num + 1
        else:  # SR
            # Индивидуальное подтверждение
            if ack_num in self.unacked:
                del self.unacked[ack_num]
            # Сдвигаем base, пока следующие по порядку пакеты подтверждены
            while (self.base < self.next_seq_num and
                   self.base not in self.unacked):
                self.base += 1

    def _check_timeouts(self):
        if self.protocol == 'GBN':
            if self.base in self.unacked:
                packet = self.unacked[self.base]
                if time.time() - packet.send_time > self.timeout:
                    # Повторно передаём всё от base до next_seq_num - 1
                    for seq in range(self.base, self.next_seq_num):
                        self._transmit(seq)
        else:  # SR
            now = time.time()
            for seq in list(self.unacked.keys()):
                packet = self.unacked[seq]
                if now - packet.send_time > self.timeout:
                    self._transmit(seq)

    def is_done(self):
        return self.done_event.is_set()

    def wait_done(self, timeout=None):
        return self.done_event.wait(timeout)

    @property
    def elapsed_time(self):
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    @property
    def efficiency(self):
        """k = полезные пакеты / все переданные пакеты."""
        if self.total_sent == 0:
            return 0.0
        return self.total_packets / self.total_sent