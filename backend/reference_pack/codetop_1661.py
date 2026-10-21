"""合并K个排序链表：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build_list(values):
    dummy = tail = ListNode()
    for value in values:
        tail.next = ListNode(value)
        tail = tail.next
    return dummy.next


def read_list(tokens):
    n = int(next(tokens))
    return build_list(int(next(tokens)) for _ in range(n))


def print_list(head):
    values = []
    while head:
        values.append(str(head.val))
        head = head.next
    print(" ".join(values))

import heapq
from itertools import count

def main():
    it = iter(sys.stdin.read().split())
    k = int(next(it))
    serial = count()
    heap = []
    for _ in range(k):
        head = read_list(it)
        if head:
            heapq.heappush(heap, (head.val, next(serial), head))
    dummy = tail = ListNode()
    while heap:
        _, _, node = heapq.heappop(heap)
        following = node.next
        tail.next, tail = node, node
        if following:
            heapq.heappush(heap, (following.val, next(serial), following))
    print_list(dummy.next)


if __name__ == "__main__":
    main()
