"""螺旋矩阵：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    it = iter(map(int, sys.stdin.read().split()))
    m, n = next(it), next(it)
    a = [[next(it) for _ in range(n)] for _ in range(m)]
    top, bottom, left, right = 0, m-1, 0, n-1
    answer = []
    while top <= bottom and left <= right:
        for c in range(left, right+1):
            answer.append(a[top][c])
        top += 1
        for r in range(top, bottom+1):
            answer.append(a[r][right])
        right -= 1
        if top <= bottom and left <= right:
            for c in range(right, left-1, -1):
                answer.append(a[bottom][c])
            bottom -= 1
            for r in range(bottom, top-1, -1):
                answer.append(a[r][left])
            left += 1
    print(*answer)


if __name__ == "__main__":
    main()
