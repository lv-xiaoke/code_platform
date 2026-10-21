"""最长有效括号：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    s = sys.stdin.readline().strip()
    stack, answer = [-1], 0
    for i, ch in enumerate(s):
        if ch == '(':
            stack.append(i)
        else:
            stack.pop()
            if not stack:
                stack.append(i)
            else:
                answer = max(answer, i-stack[-1])
    print(answer)


if __name__ == "__main__":
    main()
