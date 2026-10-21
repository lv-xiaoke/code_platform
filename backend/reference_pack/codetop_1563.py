"""买卖股票的最佳时机：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    it = iter(map(int, sys.stdin.read().split()))
    n = next(it)
    lowest, answer = float("inf"), 0
    for _ in range(n):
        price = next(it)
        lowest = min(lowest, price)
        answer = max(answer, price-lowest)
    print(answer)


if __name__ == "__main__":
    main()
