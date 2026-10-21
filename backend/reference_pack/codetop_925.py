"""二分查找：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    it = iter(map(int, sys.stdin.read().split()))
    n, target = next(it), next(it)
    a = [next(it) for _ in range(n)]
    left, right = 0, n - 1
    while left <= right:
        mid = (left + right) // 2
        if a[mid] == target:
            print(mid)
            return
        if a[mid] < target:
            left = mid+1
        else:
            right = mid-1
    print(-1)


if __name__ == "__main__":
    main()
