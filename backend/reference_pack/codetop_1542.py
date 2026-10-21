"""环形链表 II：本地原创 ACM Python 参考实现，非官方题解。"""
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
    n, pos = next(it), next(it)
    nodes = [ListNode(next(it)) for _ in range(n)]
    for i in range(n-1):
        nodes[i].next = nodes[i+1]
    if nodes and pos >= 0:
        nodes[-1].next = nodes[pos]
    head = nodes[0] if nodes else None
    slow = fast = head
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
        if slow is fast:
            first = head
            while first is not slow:
                first, slow = first.next, slow.next
            index, node = 0, head
            while node is not first:
                node = node.next
                index += 1
            print(index)
            return
    print(-1)


if __name__ == "__main__":
    main()
