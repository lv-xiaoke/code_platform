"""删除排序链表中的重复元素 II：本地原创 ACM Python 参考实现，非官方题解。"""
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
    dummy = tail = ListNode()
    while head:
        end = head.next
        while end and end.val == head.val:
            end = end.next
        if head.next is end:
            tail.next = head
            tail = head
        head = end
    tail.next = None
    print_list(dummy.next)


if __name__ == "__main__":
    main()
