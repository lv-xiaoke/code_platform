"""字符串相加：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    a, b = sys.stdin.readline().strip(), sys.stdin.readline().strip()
    i, j, carry = len(a)-1, len(b)-1, 0
    answer = []
    while i >= 0 or j >= 0 or carry:
        total = carry + (ord(a[i])-48 if i >= 0 else 0) + (ord(b[j])-48 if j >= 0 else 0)
        carry, digit = divmod(total, 10)
        answer.append(chr(digit+48))
        i -= 1
        j -= 1
    print("".join(reversed(answer)) or "0")


if __name__ == "__main__":
    main()
