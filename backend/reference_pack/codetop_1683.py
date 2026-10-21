"""两数之和：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    it = iter(map(int, sys.stdin.read().split()))
    n, target = next(it), next(it)
    seen = {}
    for i in range(n):
        value = next(it)
        if target - value in seen:
            print(seen[target - value], i)
            return
        seen[value] = i
    print(-1, -1)


if __name__ == "__main__":
    main()
