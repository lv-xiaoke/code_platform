"""相交链表：本地原创 ACM Python 参考实现，非官方题解。"""
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
    a, b, c = next(it), next(it), next(it)
    head_a = build_list(next(it) for _ in range(a))
    head_b = build_list(next(it) for _ in range(b))
    shared = build_list(next(it) for _ in range(c))
    def connect(head):
        if not head:
            return shared
        tail = head
        while tail.next:
            tail = tail.next
        tail.next = shared
        return head
    head_a, head_b = connect(head_a), connect(head_b)
    x, y = head_a, head_b
    while x is not y:
        x = x.next if x else head_b
        y = y.next if y else head_a
    print(x.val if x else "null")


if __name__ == "__main__":
    main()
