"""用栈实现队列：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    incoming, outgoing = [], []
    def shift():
        if not outgoing:
            while incoming:
                outgoing.append(incoming.pop())
    for _ in range(int(sys.stdin.readline())):
        op = sys.stdin.readline().split()
        if op[0] == 'push':
            incoming.append(int(op[1]))
        elif op[0] == 'empty':
            print('false' if incoming or outgoing else 'true')
        else:
            shift()
            print(outgoing.pop() if op[0] == 'pop' else outgoing[-1])


if __name__ == "__main__":
    main()
