"""合并两个有序数组：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    it = iter(map(int, sys.stdin.read().split()))
    n, m = next(it), next(it)
    a = [next(it) for _ in range(n)] + [0] * m
    b = [next(it) for _ in range(m)]
    i, j, k = n-1, m-1, n+m-1
    while j >= 0:
        if i >= 0 and a[i] > b[j]:
            a[k] = a[i]
            i -= 1
        else:
            a[k] = b[j]
            j -= 1
        k -= 1
    print(*a)


if __name__ == "__main__":
    main()
