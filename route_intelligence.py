from collections import defaultdict, deque

class RouteGraph:
    def __init__(self, routes):
        self.graph = defaultdict(list)
        self.routes = {r.id: r for r in routes}
        for route in routes:
            if route.status == 'verified':
                self.graph[route.from_location_id].append((route.to_location_id, route.fare, route.id))
                # Assuming undirected for simplicity, but fares might differ
                self.graph[route.to_location_id].append((route.from_location_id, route.fare, route.id))

    def find_direct_route(self, from_id, to_id):
        for neighbor, fare, route_id in self.graph[from_id]:
            if neighbor == to_id:
                return self.routes[route_id]
        return None

    def find_path(self, from_id, to_id):
        # BFS to find shortest path in terms of stops
        queue = deque([(from_id, [from_id], 0)])  # node, path, total_fare
        visited = set()

        while queue:
            current, path, total_fare = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            if current == to_id:
                return path, total_fare

            for neighbor, fare, _ in self.graph[current]:
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor], total_fare + fare))

        return None, None