"""三数之和：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    data = list(map(int, sys.stdin.read().split()))
    a = sorted(data[1:1 + data[0]])
    answer = []
    for i in range(len(a) - 2):
        if i and a[i] == a[i - 1]:
            continue
        left, right = i + 1, len(a) - 1
        while left < right:
            total = a[i] + a[left] + a[right]
            if total < 0:
                left += 1
            elif total > 0:
                right -= 1
            else:
                answer.append(f"{a[i]} {a[left]} {a[right]}")
                x, y = a[left], a[right]
                while left < right and a[left] == x:
                    left += 1
                while left < right and a[right] == y:
                    right -= 1
    print("\n".join(answer))


if __name__ == "__main__":
    main()
