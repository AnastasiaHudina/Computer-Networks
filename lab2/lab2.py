"""
Лабораторная работа: Моделирование протокола динамической маршрутизации OSPF.
"""
import random
import heapq
import json
import os
from collections import deque
import math

import networkx as nx
import matplotlib.pyplot as plt

# БЛОК 1: КЛАССЫ МАРШРУТИЗАТОРА И СЕТИ

class Router:
    """Класс, представляющий отдельный маршрутизатор в сети."""
    def __init__(self, router_id):
        self.id = router_id
        self.neighbors = {}      # Соседи: {id_соседа: стоимость_канала}
        self.lsdb = {}           # База данных состояния каналов (карта всей сети)
        self.routing_table = {}  # Таблица маршрутизации: {назначение: (след_узел, стоимость, путь)}

    def receive_hello(self, neighbor_id, cost):
        """Получение HELLO-пакета от соседа."""
        self.neighbors[neighbor_id] = cost

    def build_routing_table(self, full_graph):
        """Запуск алгоритма Дейкстры на основе полученной карты сети (LSDB)."""
        self.routing_table = {}
        distances = {node: float('inf') for node in full_graph}
        distances[self.id] = 0
        previous = {node: None for node in full_graph}
        pq = [(0, self.id)]

        while pq:
            current_dist, current_node = heapq.heappop(pq)
            if current_dist > distances[current_node]:
                continue
            for neighbor, weight in full_graph[current_node].items():
                distance = current_dist + weight
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current_node
                    heapq.heappush(pq, (distance, neighbor))

        for dest in full_graph:
            if dest == self.id:
                continue
            if distances[dest] == float('inf'):
                self.routing_table[dest] = (None, float('inf'), [])
            else:
                path = []
                curr = dest
                while curr is not None:
                    path.append(curr)
                    curr = previous[curr]
                path.reverse()
                next_hop = path[1] if len(path) > 1 else None
                self.routing_table[dest] = (next_hop, distances[dest], path)


class Network:
    """Класс для управления всей сетью маршрутизаторов."""
    def __init__(self, num_routers=8):
        self.num_routers = num_routers
        self.router_ids = [f"R{i}" for i in range(1, num_routers + 1)]
        self.routers = {rid: Router(rid) for rid in self.router_ids}
        self.links = []
        self.active_links = []
        self.graph = nx.Graph()

    def generate_topology(self, topology_type):
        """Генерация одной из трех топологий: line, ring, star."""
        self.links = []

        if topology_type == "line":
            for i in range(self.num_routers - 1):
                cost = random.randint(1, 9)
                self.links.append((self.router_ids[i], self.router_ids[i+1], cost))
        elif topology_type == "ring":
            for i in range(self.num_routers - 1):
                cost = random.randint(1, 9)
                self.links.append((self.router_ids[i], self.router_ids[i+1], cost))
            cost = random.randint(1, 9)
            self.links.append((self.router_ids[-1], self.router_ids[0], cost))
        elif topology_type == "star":
            center = self.router_ids[0]
            for i in range(1, self.num_routers):
                cost = random.randint(1, 9)
                self.links.append((center, self.router_ids[i], cost))

        self.active_links = list(self.links)
        self._update_graph()
        return topology_type

    def _update_graph(self):
        self.graph.clear()
        self.graph.add_nodes_from(self.router_ids)
        for u, v, w in self.active_links:
            self.graph.add_edge(u, v, weight=w)

    def run_hello_phase(self):
        for router in self.routers.values():
            router.neighbors.clear()
        for u, v, cost in self.active_links:
            self.routers[u].receive_hello(v, cost)
            self.routers[v].receive_hello(u, cost)

    def find_connected_components(self):
        visited = set()
        components = []
        for node in self.router_ids:
            if node not in visited:
                component = []
                queue = deque([node])
                visited.add(node)
                while queue:
                    curr = queue.popleft()
                    component.append(curr)
                    for neighbor in self.routers[curr].neighbors:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                components.append(component)
        return components

    def run_lsdb_sync(self):
        components = self.find_connected_components()
        for comp in components:
            leader = sorted(comp)[0]
            comp_graph = {node: {} for node in comp}
            for node in comp:
                for neighbor, cost in self.routers[node].neighbors.items():
                    if neighbor in comp:
                        comp_graph[node][neighbor] = cost
            for node in comp:
                self.routers[node].lsdb = comp_graph

    def run_spf(self):
        for router in self.routers.values():
            router.build_routing_table(router.lsdb)

    def send_packet(self, src, dst):
        if src == dst:
            return [src]
        current = src
        path = [current]
        active_edges = [(u, v) for u, v, w in self.active_links] + [(v, u) for u, v, w in self.active_links]

        while current != dst:
            if dst not in self.routers[current].routing_table:
                return None
            next_hop, cost, _ = self.routers[current].routing_table[dst]
            if next_hop is None or cost == float('inf') or (current, next_hop) not in active_edges:
                return None
            current = next_hop
            path.append(current)
        return path

    def break_links(self, probability):
        self.active_links = []
        for u, v, w in self.links:
            if random.random() > probability:
                self.active_links.append((u, v, w))
        self._update_graph()

# БЛОК 2: ОТРИСОВКА ГРАФОВ

def draw_topology(network, title, filename):
    plt.figure(figsize=(10, 6))
    pos = {}
    if "Линейная" in title:
        pos = {node: (i, 0) for i, node in enumerate(network.router_ids)}
    elif "Кольцо" in title:
        pos = nx.circular_layout(network.graph)
    elif "Звезда" in title:
        center = network.router_ids[0]
        pos[center] = (0, 0)
        for i, node in enumerate(network.router_ids[1:]):
            angle = 2 * math.pi * i / (len(network.router_ids) - 1)
            pos[node] = (math.cos(angle) * 2, math.sin(angle) * 2)

    nx.draw_networkx_nodes(network.graph, pos, node_size=700, node_color='lightblue', edgecolors='black')
    nx.draw_networkx_edges(network.graph, pos, width=2, edge_color='gray')
    nx.draw_networkx_labels(network.graph, pos, font_size=12, font_weight='bold')
    edge_labels = nx.get_edge_attributes(network.graph, 'weight')
    nx.draw_networkx_edge_labels(network.graph, pos, edge_labels=edge_labels, font_size=10)
    plt.title(title, fontsize=14)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

# БЛОК 3: ПРОВЕДЕНИЕ ЭКСПЕРИМЕНТОВ

def run_experiment():
    # ИСПРАВЛЕНИЕ: Фиксируем seed один раз в самом начале
    random.seed(42)

    topologies = ["line", "ring", "star"]
    titles = {"line": "Линейная", "ring": "Кольцо", "star": "Звезда"}

    if not os.path.exists("output"):
        os.makedirs("output")

    results = {}

    for topo in topologies:
        print(f"\n--- Тестирование топологии: {titles[topo]} ---")
        net = Network(num_routers=12)
        net.generate_topology(topo)
        draw_topology(net, f"{titles[topo]} (Исходная)", f"output/{topo}_initial.png")

        # Демонстрация для 8 узлов
        demo_net = Network(num_routers=8)
        demo_net.generate_topology(topo)
        demo_net.run_hello_phase()
        demo_net.run_lsdb_sync()
        demo_net.run_spf()

        if topo in ["line", "ring"]:
            fail_edge = ("R4", "R5")
        else:
            fail_edge = ("R1", "R5")

        demo_net.active_links = [l for l in demo_net.active_links if not (l[0] == fail_edge[0] and l[1] == fail_edge[1]) and not (l[1] == fail_edge[0] and l[0] == fail_edge[1])]
        demo_net._update_graph()
        draw_topology(demo_net, f"{titles[topo]} (Отказ {fail_edge[0]}-{fail_edge[1]})", f"output/{topo}_failed.png")

        demo_net.run_hello_phase()
        demo_net.run_lsdb_sync()
        demo_net.run_spf()

        demo_net2 = Network(num_routers=8)
        demo_net2.generate_topology(topo)
        demo_net2.run_hello_phase()
        demo_net2.run_lsdb_sync()
        demo_net2.run_spf()
        path_before = demo_net2.send_packet("R2", "R5")
        path_after = demo_net.send_packet("R2", "R5")

        print(f"Путь R2->R5 до отказа: {path_before}")
        print(f"Путь R2->R5 после отказа: {path_after}")

        results[topo] = []
        for prob_pct in range(0, 55, 5):
            prob = prob_pct / 100.0
            reachable_count = 0
            total_pairs = 0
            trials = 100

            for _ in range(trials):
                stat_net = Network(num_routers=12)
                stat_net.generate_topology(topo)
                stat_net.break_links(prob)

                stat_net.run_hello_phase()
                stat_net.run_lsdb_sync()
                stat_net.run_spf()

                for i in stat_net.router_ids:
                    for j in stat_net.router_ids:
                        if i != j:
                            total_pairs += 1
                            if stat_net.send_packet(i, j) is not None:
                                reachable_count += 1

            reach_pct = (reachable_count / total_pairs) * 100
            results[topo].append({"probability": prob_pct, "reachability": round(reach_pct, 1)})
            print(f"Вероятность отказа {prob_pct}%: Достижимость {reach_pct:.1f}%")

    with open("output/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    plt.figure(figsize=(10, 6))
    colors = {"line": "blue", "ring": "green", "star": "orange"}
    for topo in topologies:
        x = [d["probability"] for d in results[topo]]
        y = [d["reachability"] for d in results[topo]]
        plt.plot(x, y, marker='o', color=colors[topo], label=titles[topo], linewidth=2)
        
    plt.title("Зависимость достижимости пар узлов от вероятности отказа каналов", fontsize=14)
    plt.xlabel("Вероятность отказа каждого канала, %", fontsize=12)
    plt.ylabel("Достижимые пары маршрутизаторов, %", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig("output/reachability_plot.png")
    plt.close()

    print("\nГотово! Все файлы сохранены в папку 'output'.")

if __name__ == "__main__":
    run_experiment()