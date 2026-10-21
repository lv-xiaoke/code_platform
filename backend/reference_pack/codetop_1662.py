"""括号生成：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    n = int(sys.stdin.readline())
    def visit(left, right, path):
        if right == n:
            print(path)
            return
        if left < n:
            visit(left+1, right, path+'(')
        if right < left:
            visit(left, right+1, path+')')
    visit(0, 0, '')


if __name__ == "__main__":
    main()
