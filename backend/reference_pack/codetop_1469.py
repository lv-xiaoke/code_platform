"""数组中的第K个最大元素：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

import heapq

def main():
    it = iter(map(int, sys.stdin.read().split()))
    n, k = next(it), next(it)
    heap = []
    for _ in range(n):
        value = next(it)
        if len(heap) < k:
            heapq.heappush(heap, value)
        elif value > heap[0]:
            heapq.heapreplace(heap, value)
    print(heap[0])


if __name__ == "__main__":
    main()
