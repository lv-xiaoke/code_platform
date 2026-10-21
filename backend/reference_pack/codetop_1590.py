"""二叉树的中序遍历：本地原创 ACM Python 参考实现，非官方题解。"""
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
    current = read_tree(iter(sys.stdin.read().split()))
    stack, answer = [], []
    while current or stack:
        while current:
            stack.append(current)
            current = current.left
        current = stack.pop()
        answer.append(current.val)
        current = current.right
    print(*answer)


if __name__ == "__main__":
    main()
