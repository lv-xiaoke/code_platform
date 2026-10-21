"""手撕快速排序：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    data = list(map(int, sys.stdin.read().split()))
    a = data[1:1 + data[0]]
    stack = [(0, len(a) - 1)]
    while stack:
        left, right = stack.pop()
        if left >= right:
            continue
        pivot = a[(left + right) // 2]
        low, i, high = left, left, right
        while i <= high:
            if a[i] < pivot:
                a[low], a[i] = a[i], a[low]
                low += 1
                i += 1
            elif a[i] > pivot:
                a[high], a[i] = a[i], a[high]
                high -= 1
            else:
                i += 1
        stack.append((left, low - 1))
        stack.append((high + 1, right))
    print(*a)


if __name__ == "__main__":
    main()
