"""删除链表的倒数第N个节点：本地原创 ACM Python 参考实现，非官方题解。"""
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
    n, k = next(it), next(it)
    dummy = ListNode(0, build_list(next(it) for _ in range(n)))
    slow = fast = dummy
    for _ in range(k):
        fast = fast.next
    while fast.next:
        slow, fast = slow.next, fast.next
    slow.next = slow.next.next
    print_list(dummy.next)


if __name__ == "__main__":
    main()
