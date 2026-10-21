"""岛屿数量：本地原创 ACM Python 参考实现，非官方题解。"""
import sys

def main():
    m, n = map(int, sys.stdin.readline().split())
    grid = [list(sys.stdin.readline().strip()) for _ in range(m)]
    answer = 0
    for r in range(m):
        for c in range(n):
            if grid[r][c] != "1":
                continue
            answer += 1
            grid[r][c] = "0"
            stack = [(r, c)]
            while stack:
                x, y = stack.pop()
                for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if 0 <= nx < m and 0 <= ny < n and grid[nx][ny] == "1":
                        grid[nx][ny] = "0"
                        stack.append((nx, ny))
    print(answer)


if __name__ == "__main__":
    main()
