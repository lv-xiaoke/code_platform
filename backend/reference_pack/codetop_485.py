"""最长公共子序列：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    a = sys.stdin.readline().rstrip("\r\n")
    b = sys.stdin.readline().rstrip("\r\n")
    previous = [0]*(len(b)+1)
    for x in a:
        current = [0]
        for j, y in enumerate(b, 1):
            current.append(previous[j-1]+1 if x == y else max(previous[j], current[-1]))
        previous = current
    print(previous[-1])


if __name__ == "__main__":
    main()
