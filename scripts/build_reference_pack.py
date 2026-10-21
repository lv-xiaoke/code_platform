"""Author the initial original ACM learning pack; refuses to overwrite edited files."""
import json
from pathlib import Path
import textwrap

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'backend/reference_pack'
ENTRIES=[]
SOURCE=json.loads((ROOT/'vendor/algoTop-main/public/data/codetop.json').read_text(encoding='utf-8'))
BY_DISPLAY={q['displayId']:q for q in SOURCE['questions'].values()}

LIST_HELPERS='''
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build_list(values):
    dummy = tail = ListNode()
    for value in values:
        tail.next = ListNode(value)
        tail = tail.next
    return dummy.next


def read_list(tokens):
    n = int(next(tokens))
    return build_list(int(next(tokens)) for _ in range(n))


def print_list(head):
    values = []
    while head:
        values.append(str(head.val))
        head = head.next
    print(" ".join(values))
'''
TREE_HELPERS='''
from collections import deque


class TreeNode:
    def __init__(self, val):
        self.val = val
        self.left = self.right = None


def read_tree(tokens):
    n = int(next(tokens))
    values = [next(tokens) for _ in range(n)]
    if not values or values[0] == "null":
        return None
    root = TreeNode(int(values[0]))
    queue = deque([root])
    index = 1
    while queue and index < n:
        node = queue.popleft()
        for side in ("left", "right"):
            if index >= n:
                break
            value = values[index]
            index += 1
            if value != "null":
                child = TreeNode(int(value))
                setattr(node, side, child)
                queue.append(child)
    return root
'''
ARRAY_INPUT='第一行 n，随后 n 个整数（可分行）。n 是数组长度。'
LIST_INPUT='第一行 n，随后 n 个整数表示链表节点值；n=0 表示空链表。'
TREE_INPUT='第一行 n，随后 n 个层序序列项，空节点写 null；n 包含 null 项。按队列为非空节点依次分配左右孩子，n=0 表示空树。'


def add(display,input_desc,output_desc,explanation,complexity,code,samples,*,helpers='',comparison='tokens'):
    q=BY_DISPLAY[str(display)]
    program='"""'+q['title']+'：本地原创 ACM Python 参考实现，非官方题解。"""\nimport sys\n'+textwrap.dedent(helpers)+'\n'+textwrap.dedent(code).strip()+'\n\n\nif __name__ == "__main__":\n    main()\n'
    filename=f'codetop_{q["id"]}.py'
    cases=[{'id':f'builtin:{q["id"]}:{i}','name':f'样例 / 边界 {i+1}','stdin':stdin,'expected_stdout':out,'comparison':comparison} for i,(stdin,out) in enumerate(samples)]
    ENTRIES.append({'source_record_id':str(q['id']),'display_id':q['displayId'],'title':q['title'],'file':filename,'input_description':input_desc,'output_description':output_desc,'explanation':explanation,'complexity':complexity,'attribution':'本地原创学习参考（非官方题解）','cases':cases})
    write_new(TARGET/filename,program)


def write_new(path,content):
    if path.exists() and path.read_text(encoding='utf-8')!=content:
        raise RuntimeError(f'Refusing to overwrite an edited file: {path}')
    if not path.exists(): path.write_text(content,encoding='utf-8')


def main():
    TARGET.mkdir(exist_ok=True)
    add(3,'一行字符串 s，允许空行；行结束符不属于字符串。','输出最长无重复子串的长度。','滑动窗口记录字符上次出现的位置，重复时推进左边界。','时间 O(n)，空间 O(字符集大小)。','''
    def main():
        s = sys.stdin.readline().rstrip("\\r\\n")
        last = {}
        left = answer = 0
        for right, ch in enumerate(s):
            left = max(left, last.get(ch, -1) + 1)
            last[ch] = right
            answer = max(answer, right - left + 1)
        print(answer)
    ''',[('abcabcbb\n','3'),('bbbbb\n','1'),('\n','0'),('你好你世\n','3')])
    add(146,'第一行 capacity q，随后 q 行 put key value 或 get key；capacity>=1。','每次 get 输出对应值，未找到输出 -1。','OrderedDict 维护访问次序，访问移至末尾，超容量淘汰最早项。','每个操作均摊 O(1)，空间 O(capacity)。','''
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
    ''',[('2 8\nput 1 1\nput 2 2\nget 1\nput 3 3\nget 2\nput 4 4\nget 1\nget 4\n','1\n-1\n-1\n4'),('1 4\nput 1 7\nput 1 8\nget 1\nget 2\n','8\n-1'),('1 0\n','')])
    add(206,LIST_INPUT,'输出反转后节点值，以空格分隔；空链表输出空行。','迭代改变 next 指针，同时保留原后继。','时间 O(n)，额外空间 O(1)。','''
    def main():
        head = read_list(iter(sys.stdin.read().split()))
        previous = None
        while head:
            following = head.next
            head.next = previous
            previous, head = head, following
        print_list(previous)
    ''',[('5\n1 2 3 4 5\n','5 4 3 2 1'),('1\n7\n','7'),('0\n','')],helpers=LIST_HELPERS)
    add(215,'第一行 n k，随后 n 个整数；1<=k<=n。','输出第 k 大元素（保留重复计数）。','维护容量为 k 的最小堆，堆顶就是当前第 k 大元素。','时间 O(n log k)，空间 O(k)。','''
    import heapq

    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n, k = next(it), next(it)
        heap = []
        for _ in range(n):
            value = next(it)
            if len(heap) < k:
                heapq.heappush(heap, value)
            elif value > heap[0]:
                heapq.heapreplace(heap, value)
        print(heap[0])
    ''',[('6 2\n3 2 1 5 6 4\n','5'),('9 4\n3 2 3 1 2 4 5 5 6\n','4'),('1 1\n-9\n','-9')])
    add(25,'第一行 n k，随后 n 个节点值；k>=1。','每 k 个节点反转，不足 k 个保留；输出节点值。','找到每组尾节点后原地反转该组，使用哑节点连接前后段。','时间 O(n)，额外空间 O(1)。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n, k = next(it), next(it)
        dummy = ListNode(0, build_list(next(it) for _ in range(n)))
        before = dummy
        while True:
            end = before
            for _ in range(k):
                end = end.next
                if end is None:
                    print_list(dummy.next)
                    return
            after = end.next
            current = before.next
            tail = current
            previous = after
            while current is not after:
                following = current.next
                current.next = previous
                previous, current = current, following
            before.next = end
            before = tail
    ''',[('5 2\n1 2 3 4 5\n','2 1 4 3 5'),('5 3\n1 2 3 4 5\n','3 2 1 4 5'),('0 1\n','')],helpers=LIST_HELPERS)
    add(15,ARRAY_INPUT,'每行一个和为 0 的三元组，组内升序，无重复；行序不限，无解输出空行。','排序后枚举首项并用双指针寻找另外两项，跳过重复值。','时间 O(n²)，排序与结果存储另计。','''
    def main():
        data = list(map(int, sys.stdin.read().split()))
        a = sorted(data[1:1 + data[0]])
        answer = []
        for i in range(len(a) - 2):
            if i and a[i] == a[i - 1]:
                continue
            left, right = i + 1, len(a) - 1
            while left < right:
                total = a[i] + a[left] + a[right]
                if total < 0:
                    left += 1
                elif total > 0:
                    right -= 1
                else:
                    answer.append(f"{a[i]} {a[left]} {a[right]}")
                    x, y = a[left], a[right]
                    while left < right and a[left] == x:
                        left += 1
                    while left < right and a[right] == y:
                        right -= 1
        print("\\n".join(answer))
    ''',[('6\n-1 0 1 2 -1 -4\n','-1 -1 2\n-1 0 1'),('4\n0 0 0 0\n','0 0 0'),('3\n1 2 3\n','')],comparison='unordered_lines')
    add(53,ARRAY_INPUT+' n>=1。','输出非空连续子数组的最大和。','Kadane：维护必须以当前位置结束的最大和，再更新全局答案。','时间 O(n)，额外空间 O(1)。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n = next(it)
        current = answer = next(it)
        for _ in range(n - 1):
            value = next(it)
            current = max(value, current + value)
            answer = max(answer, current)
        print(answer)
    ''',[('9\n-2 1 -3 4 -1 2 1 -5 4\n','6'),('3\n-5 -2 -7\n','-2'),('1\n9\n','9')])
    add('补充题4',ARRAY_INPUT,'输出升序排序后的数组，空格分隔。','显式栈维护区间，用三路划分把小于、等于、大于基准的元素分开。','平均时间 O(n log n)，最坏 O(n²)；显式区间栈。','''
    def main():
        data = list(map(int, sys.stdin.read().split()))
        a = data[1:1 + data[0]]
        stack = [(0, len(a) - 1)]
        while stack:
            left, right = stack.pop()
            if left >= right:
                continue
            pivot = a[(left + right) // 2]
            low, i, high = left, left, right
            while i <= high:
                if a[i] < pivot:
                    a[low], a[i] = a[i], a[low]
                    low += 1
                    i += 1
                elif a[i] > pivot:
                    a[high], a[i] = a[i], a[high]
                    high -= 1
                else:
                    i += 1
            stack.append((left, low - 1))
            stack.append((high + 1, right))
        print(*a)
    ''',[('6\n5 1 1 2 0 0\n','0 0 1 1 2 5'),('4\n-3 0 8 -3\n','-3 -3 0 8'),('0\n','')])
    add(5,'一行字符串，允许空行。','输出最长回文子串；等长时输出起点最靠左者。','从奇数与偶数中心向两侧扩展，只在长度更大时替换答案。','时间 O(n²)，额外空间 O(1)。','''
    def main():
        s = sys.stdin.readline().rstrip("\\r\\n")
        start = length = 0
        for center in range(len(s)):
            for left, right in ((center, center), (center, center + 1)):
                while left >= 0 and right < len(s) and s[left] == s[right]:
                    if right - left + 1 > length:
                        start, length = left, right - left + 1
                    left -= 1
                    right += 1
        print(s[start:start + length])
    ''',[('babad\n','bab'),('cbbd\n','bb'),('\n','')])
    add(21,'先输入链表 A 的长度及节点值，再输入链表 B 的长度及节点值；两者均升序。','输出合并后的升序链表。','使用哑节点，用双指针依次连接较小节点。','时间 O(n+m)，额外空间 O(1)。','''
    def merge(a, b):
        dummy = tail = ListNode()
        while a and b:
            if a.val <= b.val:
                tail.next, a = a, a.next
            else:
                tail.next, b = b, b.next
            tail = tail.next
        tail.next = a or b
        return dummy.next

    def main():
        tokens = iter(sys.stdin.read().split())
        print_list(merge(read_list(tokens), read_list(tokens)))
    ''',[('3\n1 2 4\n3\n1 3 4\n','1 1 2 3 4 4'),('0\n1\n0\n','0'),('0\n0\n','')],helpers=LIST_HELPERS)
    bfs_code='''
    def main():
        root = read_tree(iter(sys.stdin.read().split()))
        queue = deque([root]) if root else deque()
        level = 0
        while queue:
            values = []
            for _ in range(len(queue)):
                node = queue.popleft()
                values.append(node.val)
                if node.left:
                    queue.append(node.left)
                if node.right:
                    queue.append(node.right)
            TRANSFORM
            level += 1
    '''
    add(102,TREE_INPUT,'每层输出一行，层内由左至右；空树不输出内容。','队列按当前层长度分批弹出，并把子节点加入下一层。','时间 O(n)，空间 O(树的最大宽度)。',bfs_code.replace('TRANSFORM','print(*values)'),[('7\n3 9 20 null null 15 7\n','3\n9 20\n15 7'),('1\n1\n','1'),('0\n','')],helpers=TREE_HELPERS)
    add(200,'第一行 m n，接着 m 行长度 n 的 0/1 字符串，行内不加空格。','输出上下左右相连的陆地块数。','遍历陆地，用显式栈淹没同一连通块，避免递归深度限制。','时间 O(mn)，空间 O(mn)。','''
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
    ''',[('4 5\n11000\n11000\n00100\n00011\n','3'),('1 1\n0\n','0'),('1 1\n1\n','1')])
    search_code='''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n, target = next(it), next(it)
        a = [next(it) for _ in range(n)]
        left, right = 0, n - 1
        while left <= right:
            mid = (left + right) // 2
            if a[mid] == target:
                print(mid)
                return
            BRANCH
        print(-1)
    '''
    add(33,'第一行 n target，随后 n 个不同整数，是升序数组旋转后的结果。','输出 target 的从 0 开始的下标，不存在输出 -1。','二分判断左右哪一半有序，再判断目标是否位于该范围。','时间 O(log n)，额外空间 O(1)。',search_code.replace('BRANCH','''if a[left] <= a[mid]:
                if a[left] <= target < a[mid]:
                    right = mid - 1
                else:
                    left = mid + 1
            elif a[mid] < target <= a[right]:
                left = mid + 1
            else:
                right = mid - 1'''),[('7 0\n4 5 6 7 0 1 2\n','4'),('7 3\n4 5 6 7 0 1 2\n','-1'),('1 1\n1\n','0')])
    add(1,'第一行 n target，随后 n 个整数；有解时保证答案唯一。','输出两个下标，较小者在前；无解输出 -1 -1。','哈希表保存已访问值及其下标，查找 target-value。','时间 O(n)，空间 O(n)。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n, target = next(it), next(it)
        seen = {}
        for i in range(n):
            value = next(it)
            if target - value in seen:
                print(seen[target - value], i)
                return
            seen[value] = i
        print(-1, -1)
    ''',[('4 9\n2 7 11 15\n','0 1'),('2 6\n3 3\n','0 1'),('3 20\n1 2 3\n','-1 -1')])
    add(46,ARRAY_INPUT+' 元素互不相同。','每行一个全排列，空格分隔，行序不限。','回溯选择尚未使用的下标，恢复现场后继续下一个选择。','时间 O(n·n!)，除输出外空间 O(n)。','''
    def main():
        data = list(map(int, sys.stdin.read().split()))
        a = sorted(data[1:1+data[0]])
        used = [False] * len(a)
        path = []
        def visit():
            if len(path) == len(a):
                print(*path)
                return
            for i, value in enumerate(a):
                if not used[i]:
                    used[i] = True
                    path.append(value)
                    visit()
                    path.pop()
                    used[i] = False
        visit()
    ''',[('3\n1 2 3\n','1 2 3\n1 3 2\n2 1 3\n2 3 1\n3 1 2\n3 2 1'),('1\n8\n','8'),('0\n','')],comparison='unordered_lines')
    add(20,'一行只含 ()[]{} 的字符串，允许空行。','有效输出 true，否则 false。','左括号入栈，右括号必须与栈顶匹配。','时间 O(n)，空间 O(n)。','''
    def main():
        s = sys.stdin.readline().rstrip("\\r\\n")
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
    ''',[('()[]{}\n','true'),('([)]\n','false'),('\n','true')])
    add(88,'第一行 n m，随后 n 个 A 的有效元素和 m 个 B 的元素；都已升序，不输入 A 的预留零。','输出合并后的升序数组。','为 A 预留 m 个位置，从后向前写入两个尾部的较大值。','时间 O(n+m)，额外空间 O(1)，输出数组空间另计。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n, m = next(it), next(it)
        a = [next(it) for _ in range(n)] + [0] * m
        b = [next(it) for _ in range(m)]
        i, j, k = n-1, m-1, n+m-1
        while j >= 0:
            if i >= 0 and a[i] > b[j]:
                a[k] = a[i]
                i -= 1
            else:
                a[k] = b[j]
                j -= 1
            k -= 1
        print(*a)
    ''',[('3 3\n1 2 3\n2 5 6\n','1 2 2 3 5 6'),('0 1\n1\n','1'),('0 0\n','')])
    add(121,ARRAY_INPUT,'输出仅买卖一次可以获得的最大利润；不交易为 0。','扫描中记录最低买入价，计算当日卖出的最大利润。','时间 O(n)，额外空间 O(1)。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n = next(it)
        lowest, answer = float("inf"), 0
        for _ in range(n):
            price = next(it)
            lowest = min(lowest, price)
            answer = max(answer, price-lowest)
        print(answer)
    ''',[('6\n7 1 5 3 6 4\n','5'),('5\n7 6 4 3 1\n','0'),('0\n','0')])
    add(92,'第一行 n left right，随后 n 个节点值；1<=left<=right<=n。','输出区间反转后的节点值。','定位区间之前的节点，反复把后继插到区间最前方。','时间 O(n)，额外空间 O(1)。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n, left, right = next(it), next(it), next(it)
        dummy = ListNode(0, build_list(next(it) for _ in range(n)))
        before = dummy
        for _ in range(left-1):
            before = before.next
        tail = before.next
        for _ in range(right-left):
            moved = tail.next
            tail.next = moved.next
            moved.next = before.next
            before.next = moved
        print_list(dummy.next)
    ''',[('5 2 4\n1 2 3 4 5\n','1 4 3 2 5'),('3 1 3\n1 2 3\n','3 2 1'),('1 1 1\n9\n','9')],helpers=LIST_HELPERS)
    add(300,ARRAY_INPUT,'输出严格递增子序列的最大长度。','tails[i] 记录长度 i+1 的递增子序列的最小结尾，二分替换。','时间 O(n log n)，空间 O(n)。','''
    from bisect import bisect_left

    def main():
        it = iter(map(int, sys.stdin.read().split()))
        tails = []
        for _ in range(next(it)):
            value = next(it)
            i = bisect_left(tails, value)
            if i == len(tails):
                tails.append(value)
            else:
                tails[i] = value
        print(len(tails))
    ''',[('8\n10 9 2 5 3 7 101 18\n','4'),('4\n7 7 7 7\n','1'),('0\n','0')])
    add(103,TREE_INPUT,'每层一行，第一层由左至右，之后逐层交替。','常规 BFS 得到每层节点，奇数层反转输出。','时间 O(n)，空间 O(最大宽度)。',bfs_code.replace('TRANSFORM','print(*(values[::-1] if level % 2 else values))'),[('7\n3 9 20 null null 15 7\n','3\n20 9\n15 7'),('1\n1\n','1'),('0\n','')],helpers=TREE_HELPERS)
    add(236,TREE_INPUT+' 最后另输入 p q，节点值互异，p、q 保证存在。','输出最近公共祖先的节点值。','迭代建立父指针，记录 p 的祖先集合，再从 q 向上寻找交点。','时间 O(n)，空间 O(n)。','''
    def main():
        it = iter(sys.stdin.read().split())
        root = read_tree(it)
        p, q = int(next(it)), int(next(it))
        parents = {root:None}
        nodes = {root.val:root}
        stack = [root]
        while stack:
            node = stack.pop()
            for child in (node.left, node.right):
                if child:
                    parents[child] = node
                    nodes[child.val] = child
                    stack.append(child)
        ancestors = set()
        node = nodes[p]
        while node:
            ancestors.add(node)
            node = parents[node]
        node = nodes[q]
        while node not in ancestors:
            node = parents[node]
        print(node.val)
    ''',[('11\n3 5 1 6 2 0 8 null null 7 4\n5 1\n','3'),('11\n3 5 1 6 2 0 8 null null 7 4\n5 4\n','5'),('1\n9\n9 9\n','9')],helpers=TREE_HELPERS)
    add(23,'第一行 k，随后依次输入每条链表的长度 ni 及 ni 个升序节点值。','输出合并后的全部节点值。','最小堆保存每条链表当前头节点，取出后推进该链表。','时间 O(N log k)，空间 O(k)。','''
    import heapq
    from itertools import count

    def main():
        it = iter(sys.stdin.read().split())
        k = int(next(it))
        serial = count()
        heap = []
        for _ in range(k):
            head = read_list(it)
            if head:
                heapq.heappush(heap, (head.val, next(serial), head))
        dummy = tail = ListNode()
        while heap:
            _, _, node = heapq.heappop(heap)
            following = node.next
            tail.next, tail = node, node
            if following:
                heapq.heappush(heap, (following.val, next(serial), following))
        print_list(dummy.next)
    ''',[('3\n3 1 4 5\n3 1 3 4\n2 2 6\n','1 1 2 3 4 4 5 6'),('0\n',''),('2\n0\n2 -2 3\n','-2 3')],helpers=LIST_HELPERS)
    add(54,'第一行 m n，随后 m*n 个矩阵元素，按行输入。','输出顺时针螺旋遍历结果，空格分隔。','维护上下左右边界，每绕一圈缩小边界并检查是否仍有行列。','时间 O(mn)，除输出外空间 O(1)。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        m, n = next(it), next(it)
        a = [[next(it) for _ in range(n)] for _ in range(m)]
        top, bottom, left, right = 0, m-1, 0, n-1
        answer = []
        while top <= bottom and left <= right:
            for c in range(left, right+1):
                answer.append(a[top][c])
            top += 1
            for r in range(top, bottom+1):
                answer.append(a[r][right])
            right -= 1
            if top <= bottom and left <= right:
                for c in range(right, left-1, -1):
                    answer.append(a[bottom][c])
                bottom -= 1
                for r in range(bottom, top-1, -1):
                    answer.append(a[r][left])
                left += 1
        print(*answer)
    ''',[('3 3\n1 2 3\n4 5 6\n7 8 9\n','1 2 3 6 9 8 7 4 5'),('1 3\n1 2 3\n','1 2 3'),('0 0\n','')])
    add(143,LIST_INPUT,'输出按 L0,Ln,L1,Ln-1… 重排后的链表节点值。','快慢指针找中点，反转后半段，然后交替合并。','时间 O(n)，额外空间 O(1)。','''
    def main():
        head = read_list(iter(sys.stdin.read().split()))
        if not head or not head.next:
            print_list(head)
            return
        slow = fast = head
        while fast.next and fast.next.next:
            slow, fast = slow.next, fast.next.next
        second = slow.next
        slow.next = None
        previous = None
        while second:
            following = second.next
            second.next = previous
            previous, second = second, following
        first, second = head, previous
        while second:
            a, b = first.next, second.next
            first.next = second
            second.next = a
            first, second = a, b
        print_list(head)
    ''',[('4\n1 2 3 4\n','1 4 2 3'),('5\n1 2 3 4 5\n','1 5 2 4 3'),('0\n','')],helpers=LIST_HELPERS)
    cycle_code='''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n, pos = next(it), next(it)
        nodes = [ListNode(next(it)) for _ in range(n)]
        for i in range(n-1):
            nodes[i].next = nodes[i+1]
        if nodes and pos >= 0:
            nodes[-1].next = nodes[pos]
        head = nodes[0] if nodes else None
        slow = fast = head
        while fast and fast.next:
            slow, fast = slow.next, fast.next.next
            if slow is fast:
                FOUND
                return
        print(NO_CYCLE)
    '''
    add(141,'第一行 n pos，随后 n 个节点值；pos=-1 表示无环，否则尾节点连接到从 0 开始的 pos 节点。','有环输出 true，无环输出 false。','Floyd 快慢指针，相遇说明存在环。','时间 O(n)，额外空间 O(1)，输入建链空间另计。',cycle_code.replace('FOUND','print("true")').replace('NO_CYCLE','"false"'),[('4 1\n3 2 0 -4\n','true'),('1 -1\n1\n','false'),('0 -1\n','false')],helpers=LIST_HELPERS)
    add(415,'两行非负整数字符串，不带符号和多余前导零（0 除外）。','输出相加结果的十进制字符串。','从末位开始逐位相加并传递进位，不把整个字符串转换为整数。','时间 O(n+m)，空间 O(n+m)。','''
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
    ''',[('11\n123\n','134'),('999\n1\n','1000'),('0\n0\n','0')])
    add(56,'第一行区间数 n，随后 n 对 start end；闭区间。','合并后按起点升序，每行一个区间。','按起点排序，能与当前区间重叠就扩展右端点。','时间 O(n log n)，空间 O(n)。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        intervals = sorted((next(it), next(it)) for _ in range(next(it)))
        answer = []
        for start, end in intervals:
            if answer and start <= answer[-1][1]:
                answer[-1][1] = max(answer[-1][1], end)
            else:
                answer.append([start, end])
        for interval in answer:
            print(*interval)
    ''',[('4\n1 3\n2 6\n8 10\n15 18\n','1 6\n8 10\n15 18'),('2\n1 4\n4 5\n','1 5'),('0\n','')])
    add(72,'两行字符串 word1、word2，允许空行。','输出插入、删除、替换的最少操作数。','滚动数组动态规划，dp[j] 表示当前前缀与另一个前缀的编辑距离。','时间 O(nm)，空间 O(m)。','''
    def main():
        a = sys.stdin.readline().rstrip("\\r\\n")
        b = sys.stdin.readline().rstrip("\\r\\n")
        previous = list(range(len(b)+1))
        for i, x in enumerate(a, 1):
            current = [i]
            for j, y in enumerate(b, 1):
                current.append(previous[j-1] if x == y else 1+min(previous[j], current[-1], previous[j-1]))
            previous = current
        print(previous[-1])
    ''',[('horse\nros\n','3'),('intention\nexecution\n','5'),('\nabc\n','3')])
    add(160,'第一行 a b c，随后分别输入 A 独有前缀的 a 个值、B 独有前缀的 b 个值、共享尾段的 c 个值。','相交输出第一个共享节点的值；不相交输出 null。','按输入构造共享节点身份。双指针走到尾部后转到另一条链表，相遇即交点。','时间 O(a+b+c)，算法额外空间 O(1)，建链另计。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        a, b, c = next(it), next(it), next(it)
        head_a = build_list(next(it) for _ in range(a))
        head_b = build_list(next(it) for _ in range(b))
        shared = build_list(next(it) for _ in range(c))
        def connect(head):
            if not head:
                return shared
            tail = head
            while tail.next:
                tail = tail.next
            tail.next = shared
            return head
        head_a, head_b = connect(head_a), connect(head_b)
        x, y = head_a, head_b
        while x is not y:
            x = x.next if x else head_b
            y = y.next if y else head_a
        print(x.val if x else "null")
    ''',[('2 3 3\n4 1\n5 6 1\n8 4 5\n','8'),('1 1 0\n1\n1\n','null'),('0 0 1\n9\n','9')],helpers=LIST_HELPERS)
    add(42,ARRAY_INPUT+' 高度非负。','输出可接雨水的总量。','双指针维护左右最高墙，较低一侧的蓄水量已经确定。','时间 O(n)，额外空间 O(1)。','''
    def main():
        data = list(map(int, sys.stdin.read().split()))
        a = data[1:1+data[0]]
        left, right = 0, len(a)-1
        lm = rm = answer = 0
        while left < right:
            if a[left] <= a[right]:
                lm = max(lm, a[left])
                answer += lm-a[left]
                left += 1
            else:
                rm = max(rm, a[right])
                answer += rm-a[right]
                right -= 1
        print(answer)
    ''',[('12\n0 1 0 2 1 0 1 3 2 1 2 1\n','6'),('6\n4 2 0 3 2 5\n','9'),('0\n','0')])
    add(1143,'两行字符串，允许空行。','输出最长公共子序列长度。','滚动数组 DP：字符相同则左上角加一，否则取上方与左方最大值。','时间 O(nm)，空间 O(m)。','''
    def main():
        a = sys.stdin.readline().rstrip("\\r\\n")
        b = sys.stdin.readline().rstrip("\\r\\n")
        previous = [0]*(len(b)+1)
        for x in a:
            current = [0]
            for j, y in enumerate(b, 1):
                current.append(previous[j-1]+1 if x == y else max(previous[j], current[-1]))
            previous = current
        print(previous[-1])
    ''',[('abcde\nace\n','3'),('abc\ndef\n','0'),('\nabc\n','0')])
    add(82,LIST_INPUT+' 链表已升序。','只保留原链表中没有重复出现过的节点，输出节点值。','跳过相同值的一整段，仅将长度为一的段接入答案。','时间 O(n)，额外空间 O(1)。','''
    def main():
        head = read_list(iter(sys.stdin.read().split()))
        dummy = tail = ListNode()
        while head:
            end = head.next
            while end and end.val == head.val:
                end = end.next
            if head.next is end:
                tail.next = head
                tail = head
            head = end
        tail.next = None
        print_list(dummy.next)
    ''',[('7\n1 2 3 3 4 4 5\n','1 2 5'),('5\n1 1 1 2 3\n','2 3'),('0\n','')],helpers=LIST_HELPERS)
    add(93,'一行只含数字的字符串。','每行一个合法 IPv4 地址，行序不限，无解输出空行。','回溯切分四段，每段不超过 255，且多位数不能以 0 开头。','最多 3^4 种分段尝试，额外空间 O(1)，输出另计。','''
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
        print("\\n".join(sorted(answer)))
    ''',[('25525511135\n','255.255.11.135\n255.255.111.35'),('0000\n','0.0.0.0'),('123\n','')],comparison='unordered_lines')
    add(124,TREE_INPUT+' 通常至少一个非空节点；空树约定输出 0。','输出可从任意节点开始结束、不重复经过节点的最大路径和。','迭代后序，计算每个节点向父节点贡献的单边最大值，同时更新经过本节点的双边路径。','时间 O(n)，空间 O(n)。','''
    def main():
        root = read_tree(iter(sys.stdin.read().split()))
        if not root:
            print(0)
            return
        gains = {None:0}
        answer = float('-inf')
        stack = [(root, False)]
        while stack:
            node, visited = stack.pop()
            if visited:
                left, right = max(0, gains[node.left]), max(0, gains[node.right])
                answer = max(answer, node.val+left+right)
                gains[node] = node.val+max(left,right)
            else:
                stack.append((node, True))
                if node.right:
                    stack.append((node.right, False))
                if node.left:
                    stack.append((node.left, False))
        print(answer)
    ''',[('7\n-10 9 20 null null 15 7\n','42'),('1\n-3\n','-3'),('0\n','0')],helpers=TREE_HELPERS)
    add(19,'第一行 n k，随后 n 个节点值；1<=k<=n。','输出删除倒数第 k 个节点后的链表。','快指针先走 k 步，然后两指针同步，慢指针停在待删节点之前。','时间 O(n)，额外空间 O(1)。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n, k = next(it), next(it)
        dummy = ListNode(0, build_list(next(it) for _ in range(n)))
        slow = fast = dummy
        for _ in range(k):
            fast = fast.next
        while fast.next:
            slow, fast = slow.next, fast.next
        slow.next = slow.next.next
        print_list(dummy.next)
    ''',[('5 2\n1 2 3 4 5\n','1 2 3 5'),('1 1\n1\n',''),('2 2\n1 2\n','2')],helpers=LIST_HELPERS)
    add(4,'第一行 n m，随后 n 个 A 元素和 m 个 B 元素，均升序，n+m>=1。','输出中位数，允许小数；使用浮点容差比较。','对较短数组二分划分点，使左右两部分分别有序且大小相差不超过一。','时间 O(log min(n,m))，额外空间 O(1)。','''
    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n, m = next(it), next(it)
        a = [next(it) for _ in range(n)]
        b = [next(it) for _ in range(m)]
        if n > m:
            a, b, n, m = b, a, m, n
        left, right = 0, n
        while left <= right:
            i = (left+right)//2
            j = (n+m+1)//2-i
            al = a[i-1] if i else float('-inf')
            ar = a[i] if i < n else float('inf')
            bl = b[j-1] if j else float('-inf')
            br = b[j] if j < m else float('inf')
            if al <= br and bl <= ar:
                print(max(al, bl) if (n+m)%2 else (max(al,bl)+min(ar,br))/2)
                return
            if al > br:
                right = i-1
            else:
                left = i+1
    ''',[('2 1\n1 3\n2\n','2'),('2 2\n1 2\n3 4\n','2.5'),('0 1\n7\n','7')],comparison='float')
    add(142,'第一行 n pos，随后 n 个节点值；pos=-1 无环，否则尾节点连接到下标 pos。','输出环入口的从 0 开始的下标；无环输出 -1。','Floyd 相遇后，一个指针回到头部，两者同步前进得到入口，再计算其下标。','时间 O(n)，算法额外空间 O(1)，建链另计。',cycle_code.replace('FOUND','''first = head
                while first is not slow:
                    first, slow = first.next, slow.next
                index, node = 0, head
                while node is not first:
                    node = node.next
                    index += 1
                print(index)''').replace('NO_CYCLE','-1'),[('4 1\n3 2 0 -4\n','1'),('1 0\n7\n','0'),('0 -1\n','-1')],helpers=LIST_HELPERS)
    add(165,'两行点分版本号，每段为非负整数；允许段内前导零。','前者较大输出 1，较小输出 -1，相同输出 0。','按段转换为整数并比较，缺失的尾段补零。','时间 O(n+m)，空间 O(n+m)。','''
    from itertools import zip_longest

    def main():
        a = list(map(int, sys.stdin.readline().strip().split('.')))
        b = list(map(int, sys.stdin.readline().strip().split('.')))
        for x, y in zip_longest(a, b, fillvalue=0):
            if x != y:
                print(1 if x > y else -1)
                return
        print(0)
    ''',[('1.01\n1.001\n','0'),('1.0\n1.0.0\n','0'),('0.1\n1.1\n','-1')])
    add(199,TREE_INPUT,'输出每层最右节点的值，空格分隔。','BFS 扫描每层，保留该层最后一个节点。','时间 O(n)，空间 O(最大宽度)。','''
    def main():
        root = read_tree(iter(sys.stdin.read().split()))
        queue = deque([root]) if root else deque()
        answer = []
        while queue:
            for _ in range(len(queue)):
                node = queue.popleft()
                if node.left:
                    queue.append(node.left)
                if node.right:
                    queue.append(node.right)
            answer.append(node.val)
        print(*answer)
    ''',[('7\n1 2 3 null 5 null 4\n','1 3 4'),('1\n7\n','7'),('0\n','')],helpers=TREE_HELPERS)
    add(239,'第一行 n k，随后 n 个整数；1<=k<=n。','输出每个长度 k 的滑动窗口最大值。','维护下标单调队列，移除过期下标与不可能成为最大值的队尾。','时间 O(n)，空间 O(k)。','''
    from collections import deque

    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n, k = next(it), next(it)
        a = [next(it) for _ in range(n)]
        queue, answer = deque(), []
        for i, value in enumerate(a):
            while queue and queue[0] <= i-k:
                queue.popleft()
            while queue and a[queue[-1]] <= value:
                queue.pop()
            queue.append(i)
            if i >= k-1:
                answer.append(a[queue[0]])
        print(*answer)
    ''',[('8 3\n1 3 -1 -3 5 3 6 7\n','3 3 5 5 6 7'),('1 1\n9\n','9'),('3 2\n4 4 4\n','4 4')])
    add(22,'一个非负整数 n，表示括号对数。','每行一个有效括号组合，行序不限；n=0 输出空行。','回溯时左括号不超过 n，右括号不超过已经放置的左括号。','时间与有效组合总长度成正比，辅助空间 O(n)。','''
    def main():
        n = int(sys.stdin.readline())
        def visit(left, right, path):
            if right == n:
                print(path)
                return
            if left < n:
                visit(left+1, right, path+'(')
            if right < left:
                visit(left, right+1, path+')')
        visit(0, 0, '')
    ''',[('3\n','((()))\n(()())\n(())()\n()(())\n()()()'),('1\n','()'),('0\n','')],comparison='unordered_lines')
    add(704,'第一行 n target，随后 n 个互不相同且升序的整数。','输出目标下标，不存在输出 -1。','标准闭区间二分，根据中点值缩小搜索区间。','时间 O(log n)，空间 O(1)。',search_code.replace('BRANCH','''if a[mid] < target:
                left = mid+1
            else:
                right = mid-1'''),[('6 9\n-1 0 3 5 9 12\n','4'),('6 2\n-1 0 3 5 9 12\n','-1'),('0 9\n','-1')])
    add(32,'一行只含左右圆括号的字符串，允许空行。','输出最长连续有效括号子串的长度。','栈存未匹配左括号下标，初始放 -1，遇到无法匹配的右括号重设边界。','时间 O(n)，空间 O(n)。','''
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
    ''',[('(()\n','2'),(')()())\n','4'),('\n','0')])
    add(69,'一个非负整数 x。','输出平方根的向下取整值。','二分查找满足 mid*mid<=x 的最大整数。','时间 O(log x)，空间 O(1)。','''
    def main():
        x = int(sys.stdin.readline())
        left, right = 0, x
        while left <= right:
            mid = (left+right)//2
            if mid*mid <= x:
                left = mid+1
            else:
                right = mid-1
        print(right)
    ''',[('4\n','2'),('8\n','2'),('0\n','0')])
    add(148,LIST_INPUT,'输出升序排序后的链表节点值。','自底向上归并，每轮把长度为 size 的相邻段合并，size 翻倍。','时间 O(n log n)，算法额外空间 O(1)，输入建链另计。','''
    def split(head, size):
        if not head:
            return None
        for _ in range(size-1):
            if not head.next:
                break
            head = head.next
        rest = head.next
        head.next = None
        return rest

    def main():
        it = iter(map(int, sys.stdin.read().split()))
        n = next(it)
        dummy = ListNode(0, build_list(next(it) for _ in range(n)))
        size = 1
        while size < n:
            current, tail = dummy.next, dummy
            while current:
                left = current
                right = split(left, size)
                current = split(right, size)
                while left and right:
                    if left.val <= right.val:
                        tail.next, left = left, left.next
                    else:
                        tail.next, right = right, right.next
                    tail = tail.next
                tail.next = left or right
                while tail.next:
                    tail = tail.next
            size *= 2
        print_list(dummy.next)
    ''',[('4\n4 2 1 3\n','1 2 3 4'),('5\n-1 5 3 4 0\n','-1 0 3 4 5'),('0\n','')],helpers=LIST_HELPERS)
    add(94,TREE_INPUT,'输出中序遍历的节点值，空格分隔。','显式栈模拟递归：先走到最左，再访问节点并转向右子树。','时间 O(n)，空间 O(h)。','''
    def main():
        current = read_tree(iter(sys.stdin.read().split()))
        stack, answer = [], []
        while current or stack:
            while current:
                stack.append(current)
                current = current.left
            current = stack.pop()
            answer.append(current.val)
            current = current.right
        print(*answer)
    ''',[('4\n1 null 2 3\n','1 3 2'),('1\n7\n','7'),('0\n','')],helpers=TREE_HELPERS)
    add(232,'第一行 q，随后 q 行 push x、pop、peek 或 empty；pop/peek 保证非空。','pop/peek 输出值；empty 输出 true/false；push 不输出。','入队压入输入栈，出队时若输出栈为空则整体倒入输出栈。','每次操作均摊 O(1)，总空间 O(n)。','''
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
    ''',[('6\npush 1\npush 2\npeek\npop\nempty\npop\n','1\n1\nfalse\n2'),('1\nempty\n','true'),('4\npush 9\npop\nempty\npush 2\n','9\ntrue')])
    add(31,ARRAY_INPUT,'输出字典序下一个排列；若已最大则输出升序最小排列。','从右找首个上升转折点，与右侧刚好更大的数交换，再反转右侧降序段。','时间 O(n)，额外空间 O(1)。','''
    def main():
        data = list(map(int, sys.stdin.read().split()))
        a = data[1:1+data[0]]
        i = len(a)-2
        while i >= 0 and a[i] >= a[i+1]:
            i -= 1
        if i >= 0:
            j = len(a)-1
            while a[j] <= a[i]:
                j -= 1
            a[i], a[j] = a[j], a[i]
        left, right = i+1, len(a)-1
        while left < right:
            a[left], a[right] = a[right], a[left]
            left += 1
            right -= 1
        print(*a)
    ''',[('3\n1 2 3\n','1 3 2'),('3\n3 2 1\n','1 2 3'),('3\n1 1 5\n','1 5 1')])
    add(76,'两行字符串 s、t，允许空行。','输出覆盖 t 全部字符及重复次数的最短子串；等长取最左，无解输出空行。','滑动窗口统计欠缺字符；全部覆盖后收缩左边界并更新答案。','时间 O(n+m)，空间 O(字符集大小)。','''
    from collections import Counter

    def main():
        s = sys.stdin.readline().rstrip("\\r\\n")
        t = sys.stdin.readline().rstrip("\\r\\n")
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
    ''',[('ADOBECODEBANC\nABC\n','BANC'),('a\naa\n',''),('aa\naa\n','aa'),('abc\n\n','')])
    expected={str(r['questionId']) for r in SOURCE['indexes']['overall'][:50]}
    actual={e['source_record_id'] for e in ENTRIES}
    if expected!=actual: raise RuntimeError(f'Coverage mismatch: missing={expected-actual}, extra={actual-expected}')
    manifest={'version':'2026-10-21-v1','attribution':'Original local learning references, not official solutions.','problems':ENTRIES}
    write_new(TARGET/'manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(f'Created {len(ENTRIES)} complete Python references and {sum(len(e["cases"]) for e in ENTRIES)} golden cases.')


if __name__=='__main__': main()
