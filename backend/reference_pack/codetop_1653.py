"""下一个排列：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    data = list(map(int, sys.stdin.read().split()))
    a = data[1:1+data[0]]
    i = len(a)-2
    while i >= 0 and a[i] >= a[i+1]:
        i -= 1
    if i >= 0:
        j = len(a)-1
        while a[j] <= a[i]:
            j -= 1
        a[i], a[j] = a[j], a[i]
    left, right = i+1, len(a)-1
    while left < right:
        a[left], a[right] = a[right], a[left]
        left += 1
        right -= 1
    print(*a)


if __name__ == "__main__":
    main()
