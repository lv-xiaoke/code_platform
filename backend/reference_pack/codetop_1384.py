"""最长上升子序列：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

from bisect import bisect_left

def main():
    it = iter(map(int, sys.stdin.read().split()))
    tails = []
    for _ in range(next(it)):
        value = next(it)
        i = bisect_left(tails, value)
        if i == len(tails):
            tails.append(value)
        else:
            tails[i] = value
    print(len(tails))


if __name__ == "__main__":
    main()
