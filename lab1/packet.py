class Packet:
    def __init__(self, seq_num=0, data=None, is_ack=False, ack_num=None):
        """
        seq_num: порядковый номер пакета данных (для ACK может быть 0)
        data: полезная нагрузка (строка или байты), для ACK не используется
        is_ack: True, если это подтверждение
        ack_num: номер подтверждаемого пакета (только для ACK)
        send_time: время отправки (заполняется отправителем)
        """
        self.seq_num = seq_num
        self.data = data
        self.is_ack = is_ack
        self.ack_num = ack_num
        self.send_time = None  # будет установлено при отправке

    def __repr__(self):
        if self.is_ack:
            return f"ACK(ack_num={self.ack_num})"
        return f"DATA(seq_num={self.seq_num})"