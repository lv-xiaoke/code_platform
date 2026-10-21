"""有效的括号：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    s = sys.stdin.readline().rstrip("\r\n")
    stack = []
    pairs = {')':'(', ']':'[', '}':'{'}
    for ch in s:
        if ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                print("false")
                return
        else:
            stack.append(ch)
    print("false" if stack else "true")


if __name__ == "__main__":
    main()
