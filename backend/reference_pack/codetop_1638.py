"""全排列：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    data = list(map(int, sys.stdin.read().split()))
    a = sorted(data[1:1+data[0]])
    used = [False] * len(a)
    path = []
    def visit():
        if len(path) == len(a):
            print(*path)
            return
        for i, value in enumerate(a):
            if not used[i]:
                used[i] = True
                path.append(value)
                visit()
                path.pop()
                used[i] = False
    visit()


if __name__ == "__main__":
    main()
