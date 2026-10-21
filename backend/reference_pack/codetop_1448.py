"""二叉树的最近公共祖先：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

from collections import deque


class TreeNode:
    def __init__(self, val):
        self.val = val
        self.left = self.right = None


def read_tree(tokens):
    n = int(next(tokens))
    values = [next(tokens) for _ in range(n)]
    if not values or values[0] == "null":
        return None
    root = TreeNode(int(values[0]))
    queue = deque([root])
    index = 1
    while queue and index < n:
        node = queue.popleft()
        for side in ("left", "right"):
            if index >= n:
                break
            value = values[index]
            index += 1
            if value != "null":
                child = TreeNode(int(value))
                setattr(node, side, child)
                queue.append(child)
    return root

def main():
    it = iter(sys.stdin.read().split())
    root = read_tree(it)
    p, q = int(next(it)), int(next(it))
    parents = {root:None}
    nodes = {root.val:root}
    stack = [root]
    while stack:
        node = stack.pop()
        for child in (node.left, node.right):
            if child:
                parents[child] = node
                nodes[child.val] = child
                stack.append(child)
    ancestors = set()
    node = nodes[p]
    while node:
        ancestors.add(node)
        node = parents[node]
    node = nodes[q]
    while node not in ancestors:
        node = parents[node]
    print(node.val)


if __name__ == "__main__":
    main()
