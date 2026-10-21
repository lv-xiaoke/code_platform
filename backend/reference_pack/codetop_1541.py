"""重排链表：本地原创 ACM Python 参考实现，非官方题解。"""
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
    head = read_list(iter(sys.stdin.read().split()))
    if not head or not head.next:
        print_list(head)
        return
    slow = fast = head
    while fast.next and fast.next.next:
        slow, fast = slow.next, fast.next.next
    second = slow.next
    slow.next = None
    previous = None
    while second:
        following = second.next
        second.next = previous
        previous, second = second, following
    first, second = head, previous
    while second:
        a, b = first.next, second.next
        first.next = second
        second.next = a
        first, second = a, b
    print_list(head)


if __name__ == "__main__":
    main()
