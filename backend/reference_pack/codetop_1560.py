"""二叉树中的最大路径和：本地原创 ACM Python 参考实现，非官方题解。"""
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
    root = read_tree(iter(sys.stdin.read().split()))
    if not root:
        print(0)
        return
    gains = {None:0}
    answer = float('-inf')
    stack = [(root, False)]
    while stack:
        node, visited = stack.pop()
        if visited:
            left, right = max(0, gains[node.left]), max(0, gains[node.right])
            answer = max(answer, node.val+left+right)
            gains[node] = node.val+max(left,right)
        else:
            stack.append((node, True))
            if node.right:
                stack.append((node.right, False))
            if node.left:
                stack.append((node.left, False))
    print(answer)


if __name__ == "__main__":
    main()
