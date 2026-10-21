"""K 个一组翻转链表：本地原创 ACM Python 参考实现，非官方题解。"""
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
    before = dummy
    while True:
        end = before
        for _ in range(k):
            end = end.next
            if end is None:
                print_list(dummy.next)
                return
        after = end.next
        current = before.next
        tail = current
        previous = after
        while current is not after:
            following = current.next
            current.next = previous
            previous, current = current, following
        before.next = end
        before = tail


if __name__ == "__main__":
    main()
