"""滑动窗口最大值：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

from collections import deque

def main():
    it = iter(map(int, sys.stdin.read().split()))
    n, k = next(it), next(it)
    a = [next(it) for _ in range(n)]
    queue, answer = deque(), []
    for i, value in enumerate(a):
        while queue and queue[0] <= i-k:
            queue.popleft()
        while queue and a[queue[-1]] <= value:
            queue.pop()
        queue.append(i)
        if i >= k-1:
            answer.append(a[queue[0]])
    print(*answer)


if __name__ == "__main__":
    main()
