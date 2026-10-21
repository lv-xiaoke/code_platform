"""LRU缓存机制：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

from collections import OrderedDict

def main():
    capacity, q = map(int, sys.stdin.readline().split())
    cache = OrderedDict()
    for _ in range(q):
        op = sys.stdin.readline().split()
        key = int(op[1])
        if op[0] == "get":
            if key in cache:
                cache.move_to_end(key)
                print(cache[key])
            else:
                print(-1)
        else:
            cache[key] = int(op[2])
            cache.move_to_end(key)
            if len(cache) > capacity:
                cache.popitem(last=False)


if __name__ == "__main__":
    main()
