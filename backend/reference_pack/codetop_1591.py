"""复原IP地址：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    s = sys.stdin.readline().strip()
    answer = []
    def visit(index, parts):
        if len(parts) == 4:
            if index == len(s):
                answer.append(".".join(parts))
            return
        if not 4-len(parts) <= len(s)-index <= 3*(4-len(parts)):
            return
        for size in range(1, 4):
            value = s[index:index+size]
            if len(value) != size or (size > 1 and value[0] == '0') or int(value) > 255:
                continue
            visit(index+size, parts+[value])
    visit(0, [])
    print("\n".join(sorted(answer)))


if __name__ == "__main__":
    main()
