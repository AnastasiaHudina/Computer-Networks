import csv
import matplotlib
import matplotlib.pyplot as plt

# Кириллица в подписях
matplotlib.rcParams['font.family'] = 'DejaVu Sans'


RESULTS_CSV = 'results.csv'


# Чтение и подготовка данных

def load_results(filename=RESULTS_CSV):
    """Прочитать CSV и вернуть список словарей с приведёнными типами."""
    rows = []
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                'protocol': r['protocol'],
                'window_size': int(r['window_size']),
                'loss_probability': float(r['loss_probability']),
                'timeout': float(r['timeout']),
                'total_packets': int(r['total_packets']),
                'k_mean': float(r['k_mean']),
                'k_stdev': float(r['k_stdev']),
                't_mean': float(r['t_mean']),
                't_stdev': float(r['t_stdev']),
                'overhead_mean': float(r['overhead_mean']),
                'overhead_stdev': float(r['overhead_stdev']),
                'total_sent_mean': float(r['total_sent_mean']),
                'finished_ratio': float(r['finished_ratio']),
            })
    return rows


def extract_curve(rows, protocol, window_size):
    """Отфильтровать строки по протоколу и окну, отсортировать по p."""
    filtered = [r for r in rows
                if r['protocol'] == protocol and r['window_size'] == window_size]
    filtered.sort(key=lambda r: r['loss_probability'])
    p = [r['loss_probability'] for r in filtered]
    return filtered, p


# Теоретические формулы

def theoretical_overhead(protocol, window, p_error):
    """
    Аналитическая оценка накладных расходов в процентах.

    SR: H = 100 * p / (1 - p), не зависит от W.
    GBN: H = 100 * (W / E[X] - 1), где E[X] = q * (1 - q^W) / p.
    """
    if p_error == 0.0:
        return 0.0
    q = 1.0 - p_error
    if protocol == 'SR':
        attempts_per_delivered = 1.0 / q
    else:  # GBN
        expected_progress = q * (1.0 - q ** window) / p_error
        attempts_per_delivered = window / expected_progress
    return 100.0 * (attempts_per_delivered - 1.0)


# Графики: k(p) и t(p) при фиксированном окне

def plot_metric(rows, window_size, metric_key, ylabel, title, filename,
                ylim=None):
    """
    График метрики для GBN и SR при заданном размере окна.

    ylim: необязательный кортеж (ymin, ymax) для честной шкалы.
    """
    plt.figure(figsize=(8, 5))

    for protocol, color in [('GBN', 'tab:blue'), ('SR', 'tab:orange')]:
        filtered, p = extract_curve(rows, protocol, window_size)
        y = [r[metric_key] for r in filtered]
        plt.plot(p, y, marker='o', label=protocol, color=color)

    plt.xlabel('Вероятность потери пакета p')
    plt.ylabel(ylabel)
    plt.title(f'{title} (window_size = {window_size})')
    if ylim is not None:
        plt.ylim(*ylim)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f'Сохранён график: {filename}')


# Семейства графиков для разных размеров окна

def plot_family(rows, metric_key, ylabel, title, filename, ylim=None):
    """
    Семейство графиков: для каждого window_size — отдельная линия.
    Слева GBN, справа SR.

    ylim: если задан, применяется к обеим панелям, чтобы сравнение
          GBN и SR было на одной шкале.
    """
    window_sizes = sorted(set(r['window_size'] for r in rows))
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)

    for ax, protocol in zip(axes, ['GBN', 'SR']):
        for ws in window_sizes:
            filtered, p = extract_curve(rows, protocol, ws)
            y = [r[metric_key] for r in filtered]
            ax.plot(p, y, marker='o', label=f'W={ws}')
        ax.set_xlabel('Вероятность ошибки p')
        ax.set_ylabel(ylabel)
        ax.set_title(f'{protocol}: {title}')
        if ylim is not None:
            ax.set_ylim(*ylim)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend()

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f'Сохранён график: {filename}')


# Главный график задания: H(p) для разных W

def plot_overhead_family(rows, filename='plot_overhead_family.png'):
    """
    Семейство кривых H(p) для разных W: слева GBN, справа SR.
    Это основной график по формулировке задания.
    """
    window_sizes = sorted(set(r['window_size'] for r in rows))
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)

    for ax, protocol in zip(axes, ['GBN', 'SR']):
        for ws in window_sizes:
            filtered, p = extract_curve(rows, protocol, ws)
            y = [r['overhead_mean'] for r in filtered]
            ax.plot(p, y, marker='o', label=f'W={ws}')
        ax.set_xlabel('Вероятность ошибки p')
        ax.set_ylabel('Накладные расходы H, %')
        ax.set_title(f'{protocol}: зависимость H(p)')
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend()

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f'Сохранён график: {filename}')


# Сравнение GBN и SR с теорией при фиксированном W

def plot_comparison_with_theory(rows, window=8, filename=None):
    """
    Сравнение GBN и SR при заданном W.
    Сплошные линии — эксперимент, пунктир — теория.
    """
    if filename is None:
        filename = f'plot_compare_w{window}.png'

    fig, ax = plt.subplots(figsize=(9, 6))
    colors = {'GBN': 'tab:orange', 'SR': 'tab:blue'}

    for protocol in ['GBN', 'SR']:
        filtered, p = extract_curve(rows, protocol, window)
        y_sim = [r['overhead_mean'] for r in filtered]
        y_theory = [theoretical_overhead(protocol, window, pi) for pi in p]

        ax.plot(p, y_sim, marker='o', color=colors[protocol],
                label=f'{protocol} (эксперимент), W={window}')
        ax.plot(p, y_theory, linestyle='--', color=colors[protocol],
                label=f'{protocol} (теория), W={window}')

    ax.set_xlabel('Вероятность ошибки p')
    ax.set_ylabel('Накладные расходы H, %')
    ax.set_title(f'Сравнение GBN и SR с теорией при W={window}')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f'Сохранён график: {filename}')


# Точка входа

def main():
    rows = load_results()
    print(f'Загружено строк: {len(rows)}')

    if not rows:
        print('Нет данных для построения графиков.')
        return

    # 1. Основные графики при фиксированном окне.
    #    Для k фиксируем шкалу (0, 1.05), чтобы падение не выглядело
    #    преувеличенным из-за обрезанной оси.
    for ws in [8]:
        plot_metric(rows, ws, 'k_mean',
                    ylabel='Коэффициент эффективности k',
                    title='Зависимость k от вероятности ошибок',
                    filename=f'plot_k_window{ws}.png',
                    ylim=(0.0, 1.05))
        plot_metric(rows, ws, 't_mean',
                    ylabel='Время передачи t, с',
                    title='Зависимость времени передачи от вероятности ошибок',
                    filename=f'plot_t_window{ws}.png')

    # 2. Семейства графиков k(p) и t(p) по всем размерам окна.
    #    Для k снова фиксируем шкалу (0, 1.05) — обе панели сравнимы.
    plot_family(rows, 'k_mean',
                ylabel='Коэффициент эффективности k',
                title='Зависимость k от p',
                filename='plot_k_family.png',
                ylim=(0.0, 1.05))
    plot_family(rows, 't_mean',
                ylabel='Время передачи t, с',
                title='Зависимость t от p',
                filename='plot_t_family.png')

    # 3. Главный график: H(p) для разных W
    plot_overhead_family(rows, filename='plot_overhead_family.png')

    # 4. Прямое сравнение GBN и SR с теорией
    available_windows = sorted(set(r['window_size'] for r in rows))
    compare_w = 8 if 8 in available_windows else available_windows[-1]
    plot_comparison_with_theory(rows, window=compare_w,
                                filename=f'plot_compare_w{compare_w}.png')


if __name__ == '__main__':
    main()
