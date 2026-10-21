"""x 的平方根：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    x = int(sys.stdin.readline())
    left, right = 0, x
    while left <= right:
        mid = (left+right)//2
        if mid*mid <= x:
            left = mid+1
        else:
            right = mid-1
    print(right)


if __name__ == "__main__":
    main()
