"""编辑距离：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    a = sys.stdin.readline().rstrip("\r\n")
    b = sys.stdin.readline().rstrip("\r\n")
    previous = list(range(len(b)+1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(previous[j-1] if x == y else 1+min(previous[j], current[-1], previous[j-1]))
        previous = current
    print(previous[-1])


if __name__ == "__main__":
    main()
