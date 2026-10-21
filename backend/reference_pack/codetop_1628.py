"""合并区间：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    it = iter(map(int, sys.stdin.read().split()))
    intervals = sorted((next(it), next(it)) for _ in range(next(it)))
    answer = []
    for start, end in intervals:
        if answer and start <= answer[-1][1]:
            answer[-1][1] = max(answer[-1][1], end)
        else:
            answer.append([start, end])
    for interval in answer:
        print(*interval)


if __name__ == "__main__":
    main()
