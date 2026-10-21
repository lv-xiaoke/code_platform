"""比较版本号：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

from itertools import zip_longest

def main():
    a = list(map(int, sys.stdin.readline().strip().split('.')))
    b = list(map(int, sys.stdin.readline().strip().split('.')))
    for x, y in zip_longest(a, b, fillvalue=0):
        if x != y:
            print(1 if x > y else -1)
            return
    print(0)


if __name__ == "__main__":
    main()
