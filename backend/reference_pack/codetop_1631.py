"""最大子数组和：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    it = iter(map(int, sys.stdin.read().split()))
    n = next(it)
    current = answer = next(it)
    for _ in range(n - 1):
        value = next(it)
        current = max(value, current + value)
        answer = max(answer, current)
    print(answer)


if __name__ == "__main__":
    main()
