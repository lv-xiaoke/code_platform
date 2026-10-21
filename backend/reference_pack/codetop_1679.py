"""最长回文子串：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    s = sys.stdin.readline().rstrip("\r\n")
    start = length = 0
    for center in range(len(s)):
        for left, right in ((center, center), (center, center + 1)):
            while left >= 0 and right < len(s) and s[left] == s[right]:
                if right - left + 1 > length:
                    start, length = left, right - left + 1
                left -= 1
                right += 1
    print(s[start:start + length])


if __name__ == "__main__":
    main()
