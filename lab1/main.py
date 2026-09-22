from tqdm import tqdm
import csv
import random
import statistics
from experiment import run_experiment


# === Настройки экспериментов ===

PROTOCOLS = ['GBN', 'SR']

# Фиксированные параметры
#WINDOW_SIZES         #Размеры окна. Степени двойки — удобно сопоставлять с теорией.
#LOSS_PROBABILITIES   # Вероятности потерь DATA 
#TIMEOUT              # сек
#TOTAL_PACKETS        # сколько пакетов передаём в одном прогоне
#REPEATS              # повторов для усреднения (95%-й ДИ)
#MAX_TIME             # аварийный тайм-аут одного эксперимента, сек

#1АЯ ПРОВЕРКА (~90 с)
#WINDOW_SIZES = [1, 4, 8]
#LOSS_PROBABILITIES = [0.0, 0.1, 0.2, 0.3]
#TIMEOUT = 0.05
#TOTAL_PACKETS = 200
#REPEATS = 3
#MAX_TIME = 60.0

#2АЯ ПРОВЕРКА (~10–20 минут)
WINDOW_SIZES = [1, 2, 4, 8]
LOSS_PROBABILITIES = [round(x * 0.05, 2) for x in range(0, 7)]
TIMEOUT = 0.05
TOTAL_PACKETS = 500  #1000
REPEATS = 10
MAX_TIME = 120.0

# ACK по умолчанию надёжны (согласуется с аналитической моделью).
# Если хотите дополнительно исследовать влияние потерь ACK,
# выставите, например, ACK_LOSS_PROBABILITY = None ниже.
ACK_LOSS_PROBABILITY = None

# Воспроизводимость: одинаковые последовательности случайных чисел
RANDOM_SEED = 20260916

# Выходной файл
OUTPUT_CSV = 'results.csv'


def run_all_experiments():
    """Перебрать все сочетания параметров и сохранить усреднённые результаты в CSV."""
    random.seed(RANDOM_SEED)

    rows = []
    total_combinations = len(PROTOCOLS) * len(WINDOW_SIZES) * len(LOSS_PROBABILITIES)

    pbar = tqdm(total=total_combinations, desc='Эксперименты', unit='combo')

    for protocol in PROTOCOLS:
        for window_size in WINDOW_SIZES:
            for loss_prob in LOSS_PROBABILITIES:

                pbar.set_description(
                    f'{protocol} W={window_size} p={loss_prob}'
                )

                k_values = []
                t_values = []
                total_sent_values = []
                overhead_values = []
                finished_count = 0

                for _ in range(REPEATS):
                    result = run_experiment(
                        protocol=protocol,
                        window_size=window_size,
                        timeout=TIMEOUT,
                        loss_probability=loss_prob,
                        ack_loss_probability=ACK_LOSS_PROBABILITY,
                        total_packets=TOTAL_PACKETS,
                        max_time=MAX_TIME,
                    )
                    k_values.append(result['k'])
                    t_values.append(result['t'])
                    total_sent_values.append(result['total_sent'])
                    overhead_values.append(result['overhead'])
                    if result['finished']:
                        finished_count += 1

                row = {
                    'protocol': protocol,
                    'window_size': window_size,
                    'loss_probability': loss_prob,
                    'ack_loss_probability': (
                        ACK_LOSS_PROBABILITY
                        if ACK_LOSS_PROBABILITY is not None
                        else 0.0
                    ),
                    'timeout': TIMEOUT,
                    'total_packets': TOTAL_PACKETS,
                    'repeats': REPEATS,
                    'k_mean': statistics.mean(k_values),
                    'k_stdev': statistics.pstdev(k_values) if len(k_values) > 1 else 0.0,
                    't_mean': statistics.mean(t_values),
                    't_stdev': statistics.pstdev(t_values) if len(t_values) > 1 else 0.0,
                    'overhead_mean': statistics.mean(overhead_values),
                    'overhead_stdev': (
                        statistics.pstdev(overhead_values)
                        if len(overhead_values) > 1 else 0.0
                    ),
                    'total_sent_mean': statistics.mean(total_sent_values),
                    'finished_ratio': finished_count / REPEATS,
                }
                rows.append(row)

                pbar.set_postfix(
                    H=f"{row['overhead_mean']:.1f}%",
                    k=f"{row['k_mean']:.2f}",
                    fin=f"{row['finished_ratio']:.2f}",
                )
                pbar.update(1)

    pbar.close()
    save_csv(rows, OUTPUT_CSV)
    print(f"\nРезультаты сохранены в {OUTPUT_CSV}")


def save_csv(rows, filename):
    """Сохранить список словарей в CSV."""
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == '__main__':
    run_all_experiments()