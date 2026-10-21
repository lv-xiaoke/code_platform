"""合并两个有序链表：本地原创 ACM Python 参考实现，非官方题解。"""
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

def merge(a, b):
    dummy = tail = ListNode()
    while a and b:
        if a.val <= b.val:
            tail.next, a = a, a.next
        else:
            tail.next, b = b, b.next
        tail = tail.next
    tail.next = a or b
    return dummy.next

def main():
    tokens = iter(sys.stdin.read().split())
    print_list(merge(read_list(tokens), read_list(tokens)))


if __name__ == "__main__":
    main()
