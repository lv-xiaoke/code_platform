import math


def compare_output(actual, expected, mode='tokens'):
    if mode=='tokens': return actual.split()==expected.split()
    if mode=='exact': return actual.replace('\r\n','\n')==expected.replace('\r\n','\n')
    if mode=='unordered_lines':
        normalize=lambda s: sorted(' '.join(line.split()) for line in s.splitlines() if line.strip())
        return normalize(actual)==normalize(expected)
    if mode=='float':
        try:
            left,right=list(map(float,actual.split())),list(map(float,expected.split()))
            return bool(left) and len(left)==len(right) and all(math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-6) for a,b in zip(left,right))
        except ValueError: return False
    raise ValueError('未知输出比较模式')
