import queue
import threading
from packet import Packet

class Receiver:
    def __init__(self, data_queue, ack_queue, protocol='GBN',
                 window_size=4, total_packets=100):
        """
        data_queue: очередь для приёма пакетов данных
        ack_queue: очередь для отправки подтверждений
        protocol: 'GBN' или 'SR'
        window_size: размер окна (нужен для SR, чтобы знать границы буфера)
        total_packets: сколько всего пакетов нужно доставить
        """
        self.data_queue = data_queue
        self.ack_queue = ack_queue
        self.protocol = protocol
        self.window_size = window_size
        self.total_packets = total_packets

        self.expected_seq_num = 0          # ожидаемый номер следующего пакета
        self.buffer = {}                   # буфер для SR: {seq_num: Packet}
        self.received_count = 0            # количество доставленных по порядку пакетов
        self.done_event = threading.Event()  # сигнал о завершении
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        """Запустить поток получателя."""
        self.thread.start()

    def run(self):
        """Основной цикл получателя."""
        while not self.done_event.is_set():
            try:
                packet = self.data_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # Получатель не должен получать ACK, но на всякий случай игнорируем
            if packet.is_ack:
                continue

            if self.protocol == 'GBN':
                self._handle_gbn(packet)
            else:
                self._handle_sr(packet)

    def _handle_gbn(self, packet):
        """Логика получателя для Go-Back-N."""
        if packet.seq_num == self.expected_seq_num:
            # Пакет пришёл в правильном порядке
            self.expected_seq_num += 1
            self.received_count += 1
            # Отправляем накопленный ACK для этого пакета
            ack = Packet(is_ack=True, ack_num=packet.seq_num)
            self.ack_queue.put(ack)
            if self.received_count >= self.total_packets:
                self.done_event.set()
        else:
            # Пакет вне очереди: отбрасываем, повторяем ACK для последнего принятого
            if self.expected_seq_num > 0:
                ack = Packet(is_ack=True, ack_num=self.expected_seq_num - 1)
                self.ack_queue.put(ack)
            # Если ещё ничего не принято, просто игнорируем

    def _handle_sr(self, packet):
        """Логика получателя для Selective Repeat."""
        if packet.seq_num == self.expected_seq_num:
            # Ожидаемый пакет: доставляем, отправляем ACK
            self.received_count += 1
            ack = Packet(is_ack=True, ack_num=packet.seq_num)
            self.ack_queue.put(ack)
            self.expected_seq_num += 1

            # Проверяем буфер: возможно, следующие пакеты уже накоплены
            while self.expected_seq_num in self.buffer:
                self.received_count += 1
                del self.buffer[self.expected_seq_num]
                self.expected_seq_num += 1

            if self.received_count >= self.total_packets:
                self.done_event.set()

        elif packet.seq_num > self.expected_seq_num:
            # Пакет пришёл вне очереди
            if packet.seq_num < self.expected_seq_num + self.window_size:
                # В пределах окна — буферизуем и отправляем индивидуальный ACK
                if packet.seq_num not in self.buffer:
                    self.buffer[packet.seq_num] = packet
                ack = Packet(is_ack=True, ack_num=packet.seq_num)
                self.ack_queue.put(ack)
            # Если вне окна — игнорируем (слишком далеко)

        else:
            # Дубликат или старый пакет: повторяем ACK
            ack = Packet(is_ack=True, ack_num=packet.seq_num)
            self.ack_queue.put(ack)

    def is_done(self):
        """Проверить, завершена ли доставка всех пакетов."""
        return self.done_event.is_set()

    def wait_done(self, timeout=None):
        """Ожидать завершения доставки."""
        return self.done_event.wait(timeout)