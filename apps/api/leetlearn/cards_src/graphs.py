"""Graphs — traversal with a visited set, ordering, and disjoint sets."""

from __future__ import annotations

from ..mentor.card_builder import Spec

SPECS: list[Spec] = [
    Spec(
        slug="number-of-islands",
        title="Number of Islands",
        difficulty="Medium",
        archetype="graph-traversal",
        subs={"collection": "the grid", "unit": "cell", "goal": "the island count"},
        understanding=(
            "A grid of land and water cells. Count the separate landmasses, where a "
            "landmass is a group of land cells joined edge-to-edge. Diagonal contact "
            "does not join them."
        ),
        topics=("matrix", "graph", "depth-first-search", "breadth-first-search"),
        code={
            "Depth-first exploration":
                "def numIslands(grid):\n"
                "    if not grid:\n"
                "        return 0\n"
                "    rows, cols = len(grid), len(grid[0])\n\n"
                "    def sink(r, c):\n"
                "        if r < 0 or c < 0 or r >= rows or c >= cols or grid[r][c] != '1':\n"
                "            return\n"
                "        grid[r][c] = '0'\n"
                "        sink(r + 1, c)\n"
                "        sink(r - 1, c)\n"
                "        sink(r, c + 1)\n"
                "        sink(r, c - 1)\n\n"
                "    count = 0\n"
                "    for r in range(rows):\n"
                "        for c in range(cols):\n"
                "            if grid[r][c] == '1':\n"
                "                count += 1\n"
                "                sink(r, c)\n"
                "    return count",
        },
        extra_pitfalls=(
            {"mistake": "Marking cells visited only after popping them",
             "why": "the same cell gets queued from several neighbours first",
             "symptom": "correct counts with badly degraded performance"},
        ),
        extra_rewrites=(
            "Solve it without mutating the input grid.",
            "Return the size of the largest island instead of the count.",
        ),
        verified=True,
    ),
    Spec(
        slug="clone-graph",
        title="Clone Graph",
        difficulty="Medium",
        archetype="graph-traversal",
        subs={"collection": "the graph", "unit": "node", "goal": "a deep copy"},
        understanding=(
            "Given a reference to one node in a connected undirected graph, build a "
            "complete independent copy. Every node and every edge must be duplicated, "
            "and the copy must share no objects with the original."
        ),
        topics=("graph", "hash-table", "depth-first-search"),
        code={
            "Depth-first exploration":
                "def cloneGraph(node):\n"
                "    copies = {}\n\n"
                "    def visit(n):\n"
                "        if not n:\n"
                "            return None\n"
                "        if n in copies:\n"
                "            return copies[n]\n"
                "        clone = Node(n.val)\n"
                "        copies[n] = clone\n"
                "        for neighbour in n.neighbors:\n"
                "            clone.neighbors.append(visit(neighbour))\n"
                "        return clone\n\n"
                "    return visit(node)",
        },
        extra_pitfalls=(
            {"mistake": "Recording the copy after recursing into neighbours",
             "why": "a cycle then revisits a node whose copy does not exist yet",
             "symptom": "infinite recursion on any graph with a loop"},
        ),
        verified=True,
    ),
    Spec(
        slug="course-schedule",
        title="Course Schedule",
        difficulty="Medium",
        archetype="topological-sort",
        subs={"collection": "the course list", "unit": "course", "goal": "a valid order"},
        understanding=(
            "A list of courses and their prerequisites. Decide whether it is possible "
            "to take every course — that is, whether the prerequisites can be "
            "satisfied in some order at all."
        ),
        topics=("graph", "topological-sort", "depth-first-search"),
        code={
            "Prerequisite counting":
                "from collections import deque\n\n"
                "def canFinish(numCourses, prerequisites):\n"
                "    outstanding = [0] * numCourses\n"
                "    dependents = [[] for _ in range(numCourses)]\n"
                "    for course, needs in prerequisites:\n"
                "        dependents[needs].append(course)\n"
                "        outstanding[course] += 1\n\n"
                "    ready = deque(c for c in range(numCourses) if outstanding[c] == 0)\n"
                "    done = 0\n"
                "    while ready:\n"
                "        course = ready.popleft()\n"
                "        done += 1\n"
                "        for nxt in dependents[course]:\n"
                "            outstanding[nxt] -= 1\n"
                "            if outstanding[nxt] == 0:\n"
                "                ready.append(nxt)\n"
                "    return done == numCourses",
        },
        extra_rewrites=(
            "Return an actual valid ordering rather than a yes or no.",
        ),
        verified=True,
    ),
    Spec(
        slug="number-of-connected-components-in-an-undirected-graph",
        title="Number of Connected Components",
        difficulty="Medium",
        archetype="union-find",
        subs={"collection": "the edge list", "unit": "node", "goal": "the component count"},
        understanding=(
            "Given a number of nodes and a list of undirected edges, count how many "
            "separate groups the nodes fall into. A node with no edges is a group by "
            "itself."
        ),
        topics=("graph", "union-find", "depth-first-search"),
        code={
            "Disjoint set with flattening":
                "def countComponents(n, edges):\n"
                "    parent = list(range(n))\n\n"
                "    def find(x):\n"
                "        while parent[x] != x:\n"
                "            parent[x] = parent[parent[x]]\n"
                "            x = parent[x]\n"
                "        return x\n\n"
                "    groups = n\n"
                "    for a, b in edges:\n"
                "        ra, rb = find(a), find(b)\n"
                "        if ra != rb:\n"
                "            parent[ra] = rb\n"
                "            groups -= 1\n"
                "    return groups",
        },
        verified=True,
    ),
]
