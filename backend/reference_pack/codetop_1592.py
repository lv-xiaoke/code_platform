"""反转链表 II：本地原创 ACM Python 参考实现，非官方题解。"""
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

def main():
    it = iter(map(int, sys.stdin.read().split()))
    n, left, right = next(it), next(it), next(it)
    dummy = ListNode(0, build_list(next(it) for _ in range(n)))
    before = dummy
    for _ in range(left-1):
        before = before.next
    tail = before.next
    for _ in range(right-left):
        moved = tail.next
        tail.next = moved.next
        moved.next = before.next
        before.next = moved
    print_list(dummy.next)


if __name__ == "__main__":
    main()
