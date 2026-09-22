import threading
from channel import MsgQueue
from sender import Sender
from receiver import Receiver


def run_experiment(protocol='GBN', window_size=4, timeout=0.2,
                   loss_probability=0.0, ack_loss_probability=None,
                   total_packets=100, max_time=120.0):
    """
    Запустить один эксперимент и вернуть статистику.

    Параметры:
        protocol: 'GBN' или 'SR'
        window_size: размер скользящего окна
        timeout: время ожидания подтверждения (сек)
        loss_probability: вероятность потери DATA-пакета [0, 1]
        ack_loss_probability: вероятность потери ACK [0, 1];
            если None — ACK считаются надёжными (ack_loss_probability = 0.0),
            что согласуется с аналитической моделью и изолирует влияние
            обратного канала.
        total_packets: сколько пакетов нужно передать
        max_time: аварийный тайм-аут эксперимента (сек), чтобы не зависнуть

    Возвращает:
        dict со статистикой
    """
    if ack_loss_probability is None:
        ack_loss_probability = 0.0

    # 1. Создаём каналы связи
    data_queue = MsgQueue(loss_probability=loss_probability, name="data")
    ack_queue = MsgQueue(loss_probability=ack_loss_probability, name="ack")

    # 2. Создаём отправителя и получателя
    sender = Sender(
        data_queue=data_queue,
        ack_queue=ack_queue,
        protocol=protocol,
        window_size=window_size,
        timeout=timeout,
        total_packets=total_packets,
    )
    receiver = Receiver(
        data_queue=data_queue,
        ack_queue=ack_queue,
        protocol=protocol,
        window_size=window_size,
        total_packets=total_packets,
    )

    # 3. Запускаем потоки
    receiver.start()
    sender.start()

    # 4. Ждём завершения (или аварийного тайм-аута)
    finished = sender.wait_done(timeout=max_time)

    # 5. Если не завершилось — принудительно останавливаем
    if not finished:
        sender.done_event.set()
        receiver.done_event.set()

    # 6. Даём потокам корректно завершиться
    sender.thread.join(timeout=2.0)
    receiver.thread.join(timeout=2.0)

    # 7. Собираем статистику
    elapsed = sender.elapsed_time if sender.elapsed_time is not None else max_time
    total_sent = sender.total_sent
    efficiency = total_packets / total_sent if total_sent > 0 else 0.0
    # Накладные расходы: доля «лишних» передач относительно полезных
    overhead = 100.0 * (total_sent - total_packets) / total_packets

    result = {
        'protocol': protocol,
        'window_size': window_size,
        'timeout': timeout,
        'loss_probability': loss_probability,
        'ack_loss_probability': ack_loss_probability,
        'total_packets': total_packets,
        'total_sent': total_sent,
        'k': efficiency,
        't': elapsed,
        'overhead': overhead,
        'finished': finished,
        'data_lost': data_queue.total_lost,
        'data_put': data_queue.total_put,
        'ack_lost': ack_queue.total_lost,
        'ack_put': ack_queue.total_put,
    }
    return result