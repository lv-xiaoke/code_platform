"""无重复字符的最长子串：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    s = sys.stdin.readline().rstrip("\r\n")
    last = {}
    left = answer = 0
    for right, ch in enumerate(s):
        left = max(left, last.get(ch, -1) + 1)
        last[ch] = right
        answer = max(answer, right - left + 1)
    print(answer)


if __name__ == "__main__":
    main()
