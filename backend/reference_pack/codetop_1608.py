"""最小覆盖子串：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

from collections import Counter

def main():
    s = sys.stdin.readline().rstrip("\r\n")
    t = sys.stdin.readline().rstrip("\r\n")
    if not t:
        print('')
        return
    need = Counter(t)
    missing = len(t)
    left = start = 0
    length = len(s)+1
    for right, ch in enumerate(s):
        if need[ch] > 0:
            missing -= 1
        need[ch] -= 1
        while missing == 0:
            if right-left+1 < length:
                start, length = left, right-left+1
            old = s[left]
            need[old] += 1
            if need[old] > 0:
                missing += 1
            left += 1
    print(s[start:start+length] if length <= len(s) else '')


if __name__ == "__main__":
    main()
