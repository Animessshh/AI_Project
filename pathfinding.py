
from heapq import heappush, heappop
from itertools import count
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Campus configuration
# ---------------------------------------------------------------------------

START_LOCATION = "Vivekananda"

BUILDINGS = [
    "Vivekananda",  # Cafeteria and robot starting point
    "Vedanta",
    "Charak",
    "Vaastu",
    "Chanakya",
    "Vishwakarma",
    "Visvesvaraya",
]

# Approximate conversion. Calibrate this by walking a known distance if able.
STEP_LENGTH_METRES = 0.75


def steps_to_metres(steps: float) -> float:
    """Convert a step count into approximate metres."""
    return round(steps * STEP_LENGTH_METRES, 2)


# The graph uses road junctions where the drawing shows roads joining.
# Edge values below are converted from the red step counts on the supplied map.
# If a labelled value is attached to a road segment ending at a junction, that
# junction is included as a node rather than pretending the whole segment
# directly connects two buildings.
#
# Please check the topology and each segment against the real campus. In
# particular, junction labels are descriptive placeholders, not campus names.
JUNCTIONS = [
    "West Road Junction",
    "Chanakya Road Junction",
    "Central Roundabout NW",
    "Central Roundabout NE",
    "Central Roundabout SE",
    "South Road Junction A",
    "South Road Junction B",
    "South Road Junction C",
    "East Road Junction",
    "Vishwakarma Road Junction",
    "Visvesvaraya Road Junction",
]

# Store the original step counts here so that the conversion assumption is
# visible and easy to update. Each tuple is (node_a, node_b, step_count).
ROAD_SEGMENTS_IN_STEPS = [
    # Upper loop and northern campus roads
    ("Vivekananda", "West Road Junction", 0),  # Building meets this junction on sketch
    ("West Road Junction", "Vishwakarma Road Junction", 110),
    ("West Road Junction", "Chanakya Road Junction", 60),
    ("Vishwakarma Road Junction", "Vishwakarma", 0),
    ("Vishwakarma Road Junction", "East Road Junction", 75),
    ("East Road Junction", "Visvesvaraya Road Junction", 20),
    ("Visvesvaraya Road Junction", "Visvesvaraya", 50),

    # Chanakya and central roundabout
    ("Chanakya Road Junction", "Chanakya", 0),
    ("Chanakya Road Junction", "Central Roundabout NW", 63),
    ("Chanakya", "Central Roundabout NW", 30),
    ("Chanakya", "Central Roundabout NE", 20),
    ("Central Roundabout NW", "Central Roundabout NE", 0),  # roundabout arc is represented below
    ("Central Roundabout NE", "East Road Junction", 90),
    ("Central Roundabout NE", "Central Roundabout SE", 70),
    ("Central Roundabout NW", "Vaastu", 100),

    # Lower campus roads
    ("Central Roundabout SE", "South Road Junction A", 85),
    ("Vaastu", "South Road Junction A", 10),
    ("Vaastu", "South Road Junction B", 20),
    ("Charak", "South Road Junction B", 20),
    ("Charak", "South Road Junction C", 20),
    ("South Road Junction B", "South Road Junction C", 40),
    ("South Road Junction C", "Vedanta", 20),
    ("South Road Junction A", "Vedanta", 0),
]

def _build_graph() -> Dict[str, Dict[str, float]]:
    """Build an undirected adjacency dictionary from the road-segment list."""
    graph: Dict[str, Dict[str, float]] = {}
    for building in BUILDINGS:
        graph[building] = {}
    for junction in JUNCTIONS:
        graph[junction] = {}

    for node_a, node_b, steps in ROAD_SEGMENTS_IN_STEPS:
        distance = steps_to_metres(steps)
        graph.setdefault(node_a, {})
        graph.setdefault(node_b, {})
        graph[node_a][node_b] = distance
        graph[node_b][node_a] = distance

    return graph


campus_graph = _build_graph()


# ---------------------------------------------------------------------------
# Shared validation
# ---------------------------------------------------------------------------

def _validate_location(graph: dict, location: str) -> None:
    if location not in graph:
        raise ValueError(
            f"Unknown location: {location!r}. "
            f"Available locations: {', '.join(graph.keys())}"
        )


def _reconstruct_path(parent: dict, goal: str) -> List[str]:
    path = [goal]
    while path[-1] in parent:
        path.append(parent[path[-1]])
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# BFS: fewest edges, treating all roads as unweighted
# ---------------------------------------------------------------------------

def bfs(graph: dict, start: str, goal: str) -> Optional[List[str]]:
    """
    Return a path with the fewest edges, or None if unreachable.

    Return format:
        list[str]  -- path from start to goal, including both endpoints
        None       -- no path exists

    BFS treats every edge equally; it does NOT minimize metres.
    """
    _validate_location(graph, start)
    _validate_location(graph, goal)

    queue = [start]
    head = 0
    visited = {start}
    parent = {}

    while head < len(queue):
        current = queue[head]
        head += 1

        if current == goal:
            return _reconstruct_path(parent, goal)

        for neighbour in graph[current]:
            if neighbour not in visited:
                visited.add(neighbour)
                parent[neighbour] = current
                queue.append(neighbour)

    return None


# ---------------------------------------------------------------------------
# DFS: find a valid path using depth-first traversal
# ---------------------------------------------------------------------------

def dfs(graph: dict, start: str, goal: str) -> Optional[List[str]]:
    """
    Return a valid path found by depth-first search, or None if unreachable.

    Return format:
        list[str]  -- path from start to goal, including both endpoints
        None       -- no path exists

    DFS does not guarantee the fewest edges or least distance.
    """
    _validate_location(graph, start)
    _validate_location(graph, goal)

    stack = [start]
    visited = {start}
    parent = {}

    while stack:
        current = stack.pop()

        if current == goal:
            return _reconstruct_path(parent, goal)

        # Reversed insertion makes traversal order predictable for this graph.
        for neighbour in reversed(list(graph[current].keys())):
            if neighbour not in visited:
                visited.add(neighbour)
                parent[neighbour] = current
                stack.append(neighbour)

    return None


# ---------------------------------------------------------------------------
# A*: least-distance route
# ---------------------------------------------------------------------------

def astar(
    graph: dict,
    start: str,
    goal: str,
    heuristic=None,
) -> Tuple[Optional[List[str]], float]:
    """
    Return the least-cost path and total distance.

    Return format:
        (path, distance) -- path is a list of locations and distance is metres
        (None, inf)       -- no path exists

    If no heuristic is supplied, h(n)=0 is used. This is admissible and makes
    this implementation equivalent to Dijkstra's algorithm, guaranteeing a
    least-distance path for non-negative edge weights. The supplied sketch
    gives relative positions but not reliable coordinates, so a zero heuristic
    is safer than inventing coordinates.

    A custom heuristic can be supplied as heuristic(node, goal). It must be
    admissible (never overestimate remaining distance) for optimality.
    """
    _validate_location(graph, start)
    _validate_location(graph, goal)

    if heuristic is None:
        heuristic = lambda node, target: 0.0

    if start == goal:
        return [start], 0.0

    tie_breaker = count()
    open_heap = []
    heappush(open_heap, (heuristic(start, goal), next(tie_breaker), 0.0, start))

    parent = {}
    best_cost = {start: 0.0}
    closed = set()

    while open_heap:
        _, _, current_cost, current = heappop(open_heap)

        # Ignore an outdated heap entry.
        if current_cost > best_cost.get(current, float("inf")):
            continue

        if current == goal:
            return _reconstruct_path(parent, goal), round(current_cost, 2)

        if current in closed:
            continue
        closed.add(current)

        for neighbour, edge_cost in graph[current].items():
            if edge_cost < 0:
                raise ValueError("A* requires non-negative edge distances.")

            new_cost = current_cost + edge_cost
            if new_cost < best_cost.get(neighbour, float("inf")):
                best_cost[neighbour] = new_cost
                parent[neighbour] = current
                closed.discard(neighbour)
                priority = new_cost + heuristic(neighbour, goal)
                heappush(
                    open_heap,
                    (priority, next(tie_breaker), new_cost, neighbour),
                )

    return None, float("inf")


# ---------------------------------------------------------------------------
# Optional command-line demonstration
# ---------------------------------------------------------------------------

def print_route(label: str, path: Optional[List[str]]) -> None:
    if path is None:
        print(f"{label}: No route found")
    else:
        print(f"{label}: {' -> '.join(path)}")


if __name__ == "__main__":
    print(f"Assumed step length: {STEP_LENGTH_METRES} metres per step")
    print("Distances are estimates converted from the red step counts.")
    print()

    for destination in BUILDINGS:
        if destination == START_LOCATION:
            continue

        print(f"Destination: {destination}")
        print_route("  BFS", bfs(campus_graph, START_LOCATION, destination))
        print_route("  DFS", dfs(campus_graph, START_LOCATION, destination))
        path, distance = astar(campus_graph, START_LOCATION, destination)

        if path is None:
            print("  A*: No route found")
        else:
            print(f"  A*: {' -> '.join(path)} ({distance:.2f} metres)")
        print()