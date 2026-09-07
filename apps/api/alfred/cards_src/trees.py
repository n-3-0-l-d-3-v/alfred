"""Trees — recursion, level order, and the search-tree ordering."""

from __future__ import annotations

from ..mentor.card_builder import Spec

SPECS: list[Spec] = [
    Spec(
        slug="invert-binary-tree",
        title="Invert Binary Tree",
        difficulty="Easy",
        archetype="tree-dfs",
        subs={"collection": "the tree", "unit": "node", "goal": "the mirrored tree"},
        understanding=(
            "Given the root of a binary tree, swap every node's left and right child "
            "so the whole tree becomes its own mirror image. Return the root."
        ),
        topics=("tree", "depth-first-search", "recursion"),
        code={
            "Recursive depth-first":
                "def invertTree(root):\n"
                "    if not root:\n"
                "        return None\n"
                "    root.left, root.right = invertTree(root.right), invertTree(root.left)\n"
                "    return root",
            "Iterative with an explicit stack":
                "def invertTree(root):\n"
                "    stack = [root]\n"
                "    while stack:\n"
                "        node = stack.pop()\n"
                "        if not node:\n"
                "            continue\n"
                "        node.left, node.right = node.right, node.left\n"
                "        stack.append(node.left)\n"
                "        stack.append(node.right)\n"
                "    return root",
        },
        verified=True,
    ),
    Spec(
        slug="maximum-depth-of-binary-tree",
        title="Maximum Depth of Binary Tree",
        difficulty="Easy",
        archetype="tree-dfs",
        subs={"collection": "the tree", "unit": "node", "goal": "the depth"},
        understanding=(
            "Return the number of nodes along the longest path from the root down to "
            "any leaf. An empty tree has depth zero."
        ),
        topics=("tree", "depth-first-search", "breadth-first-search"),
        code={
            "Recursive depth-first":
                "def maxDepth(root):\n"
                "    if not root:\n"
                "        return 0\n"
                "    return 1 + max(maxDepth(root.left), maxDepth(root.right))",
            "Iterative with an explicit stack":
                "def maxDepth(root):\n"
                "    stack = [(root, 1)] if root else []\n"
                "    best = 0\n"
                "    while stack:\n"
                "        node, depth = stack.pop()\n"
                "        best = max(best, depth)\n"
                "        if node.left:\n"
                "            stack.append((node.left, depth + 1))\n"
                "        if node.right:\n"
                "            stack.append((node.right, depth + 1))\n"
                "    return best",
        },
        verified=True,
    ),
    Spec(
        slug="diameter-of-binary-tree",
        title="Diameter of Binary Tree",
        difficulty="Easy",
        archetype="tree-dfs",
        subs={"collection": "the tree", "unit": "node", "goal": "the longest path"},
        understanding=(
            "Find the length of the longest path between any two nodes, measured in "
            "edges. That path does not have to pass through the root."
        ),
        topics=("tree", "depth-first-search", "recursion"),
        code={
            "Recursive depth-first":
                "def diameterOfBinaryTree(root):\n"
                "    best = 0\n\n"
                "    def height(node):\n"
                "        nonlocal best\n"
                "        if not node:\n"
                "            return 0\n"
                "        left = height(node.left)\n"
                "        right = height(node.right)\n"
                "        best = max(best, left + right)\n"
                "        return 1 + max(left, right)\n\n"
                "    height(root)\n"
                "    return best",
        },
        extra_pitfalls=(
            {"mistake": "Returning the diameter from the recursion",
             "why": "the parent needs a height it can extend, not a finished path",
             "symptom": "answers that only count paths through the root"},
        ),
        extra_rewrites=(
            "Explain why the value returned upward differs from the value being tracked.",
        ),
        verified=True,
    ),
    Spec(
        slug="binary-tree-level-order-traversal",
        title="Binary Tree Level Order Traversal",
        difficulty="Medium",
        archetype="tree-bfs",
        subs={"collection": "the tree", "unit": "node", "goal": "the values by level"},
        understanding=(
            "Return the node values grouped by depth: the root's level first, then "
            "everything one step below it, and so on. Each level is its own list, "
            "left to right."
        ),
        topics=("tree", "breadth-first-search", "queue"),
        code={
            "Level-by-level breadth-first":
                "from collections import deque\n\n"
                "def levelOrder(root):\n"
                "    if not root:\n"
                "        return []\n"
                "    out = []\n"
                "    q = deque([root])\n"
                "    while q:\n"
                "        level = []\n"
                "        for _ in range(len(q)):\n"
                "            node = q.popleft()\n"
                "            level.append(node.val)\n"
                "            if node.left:\n"
                "                q.append(node.left)\n"
                "            if node.right:\n"
                "                q.append(node.right)\n"
                "        out.append(level)\n"
                "    return out",
        },
        verified=True,
    ),
    Spec(
        slug="validate-binary-search-tree",
        title="Validate Binary Search Tree",
        difficulty="Medium",
        archetype="bst-property",
        subs={"collection": "the tree", "unit": "node", "goal": "a valid ordering"},
        understanding=(
            "Decide whether a binary tree satisfies the search-tree property: every "
            "value in a node's left subtree is smaller than it, everything in the "
            "right subtree is larger, and both subtrees are themselves valid."
        ),
        topics=("tree", "binary-search-tree", "depth-first-search"),
        code={
            "Ordered descent":
                "def isValidBST(root):\n"
                "    def check(node, low, high):\n"
                "        if not node:\n"
                "            return True\n"
                "        if not (low < node.val < high):\n"
                "            return False\n"
                "        return check(node.left, low, node.val) and check(node.right, node.val, high)\n\n"
                "    return check(root, float('-inf'), float('inf'))",
        },
        extra_rewrites=(
            "Solve it by checking that an in-order traversal is strictly increasing.",
        ),
        verified=True,
    ),
    Spec(
        slug="lowest-common-ancestor-of-a-binary-search-tree",
        title="Lowest Common Ancestor of a BST",
        difficulty="Medium",
        archetype="bst-property",
        subs={"collection": "the tree", "unit": "node", "goal": "the shared ancestor"},
        understanding=(
            "Given two nodes in a binary search tree, find the deepest node that has "
            "both of them somewhere beneath it. A node counts as its own descendant."
        ),
        topics=("tree", "binary-search-tree"),
        code={
            "Ordered descent":
                "def lowestCommonAncestor(root, p, q):\n"
                "    node = root\n"
                "    while node:\n"
                "        if p.val < node.val and q.val < node.val:\n"
                "            node = node.left\n"
                "        elif p.val > node.val and q.val > node.val:\n"
                "            node = node.right\n"
                "        else:\n"
                "            return node",
        },
        extra_rewrites=(
            "Solve the same problem for an unordered binary tree and compare the cost.",
        ),
        verified=True,
    ),
]
