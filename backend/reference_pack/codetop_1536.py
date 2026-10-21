"""排序链表：本地原创 ACM Python 参考实现，非官方题解。"""
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

def split(head, size):
    if not head:
        return None
    for _ in range(size-1):
        if not head.next:
            break
        head = head.next
    rest = head.next
    head.next = None
    return rest

def main():
    it = iter(map(int, sys.stdin.read().split()))
    n = next(it)
    dummy = ListNode(0, build_list(next(it) for _ in range(n)))
    size = 1
    while size < n:
        current, tail = dummy.next, dummy
        while current:
            left = current
            right = split(left, size)
            current = split(right, size)
            while left and right:
                if left.val <= right.val:
                    tail.next, left = left, left.next
                else:
                    tail.next, right = right, right.next
                tail = tail.next
            tail.next = left or right
            while tail.next:
                tail = tail.next
        size *= 2
    print_list(dummy.next)


if __name__ == "__main__":
    main()
