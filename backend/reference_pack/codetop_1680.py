"""寻找两个正序数组的中位数：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    it = iter(map(int, sys.stdin.read().split()))
    n, m = next(it), next(it)
    a = [next(it) for _ in range(n)]
    b = [next(it) for _ in range(m)]
    if n > m:
        a, b, n, m = b, a, m, n
    left, right = 0, n
    while left <= right:
        i = (left+right)//2
        j = (n+m+1)//2-i
        al = a[i-1] if i else float('-inf')
        ar = a[i] if i < n else float('inf')
        bl = b[j-1] if j else float('-inf')
        br = b[j] if j < m else float('inf')
        if al <= br and bl <= ar:
            print(max(al, bl) if (n+m)%2 else (max(al,bl)+min(ar,br))/2)
            return
        if al > br:
            right = i-1
        else:
            left = i+1


if __name__ == "__main__":
    main()
