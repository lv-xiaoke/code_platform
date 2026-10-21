"""接雨水：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    data = list(map(int, sys.stdin.read().split()))
    a = data[1:1+data[0]]
    left, right = 0, len(a)-1
    lm = rm = answer = 0
    while left < right:
        if a[left] <= a[right]:
            lm = max(lm, a[left])
            answer += lm-a[left]
            left += 1
        else:
            rm = max(rm, a[right])
            answer += rm-a[right]
            right -= 1
    print(answer)


if __name__ == "__main__":
    main()
