"""Generic-password Keychain items, without shell arguments or plaintext files."""
import ctypes as c
from contextlib import contextmanager
from functools import lru_cache

MISSING = -25300
DUPLICATE = -25299


@lru_cache(maxsize=1)
def libraries():
    cf = c.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    security = c.CDLL('/System/Library/Frameworks/Security.framework/Security')
    signatures = {
        'CFStringCreateWithCString': (c.c_void_p, [c.c_void_p, c.c_char_p, c.c_uint32]),
        'CFDataCreate': (c.c_void_p, [c.c_void_p, c.c_void_p, c.c_long]),
        'CFDataGetLength': (c.c_long, [c.c_void_p]),
        'CFDataGetBytePtr': (c.c_void_p, [c.c_void_p]),
        'CFDictionaryCreateMutable': (c.c_void_p, [c.c_void_p, c.c_long, c.c_void_p, c.c_void_p]),
        'CFDictionarySetValue': (None, [c.c_void_p, c.c_void_p, c.c_void_p]),
        'CFRelease': (None, [c.c_void_p]),
    }
    for name, (result, args) in signatures.items():
        function = getattr(cf, name)
        function.restype, function.argtypes = result, args
    for name, args in {
        'SecItemCopyMatching': [c.c_void_p, c.POINTER(c.c_void_p)],
        'SecItemUpdate': [c.c_void_p, c.c_void_p],
        'SecItemAdd': [c.c_void_p, c.c_void_p],
        'SecItemDelete': [c.c_void_p],
    }.items():
        function = getattr(security, name)
        function.restype, function.argtypes = c.c_int32, args
    return cf, security


class Objects:
    def __init__(self, cf, security):
        self.cf, self.security, self.owned = cf, security, []

    def keep(self, value):
        if not value:
            raise ValueError('钥匙串存储内存分配失败')
        self.owned.append(value)
        return value

    def constant(self, name):
        lib = self.cf if name.startswith('kCF') else self.security
        return c.c_void_p.in_dll(lib, name).value

    def string(self, value):
        return self.keep(self.cf.CFStringCreateWithCString(None, value.encode('utf-8'), 0x08000100))

    def data(self, value):
        raw = value.encode('utf-8')
        return self.keep(self.cf.CFDataCreate(None, raw, len(raw)))

    def dictionary(self, pairs):
        keys = c.byref(c.c_byte.in_dll(self.cf, 'kCFTypeDictionaryKeyCallBacks'))
        values = c.byref(c.c_byte.in_dll(self.cf, 'kCFTypeDictionaryValueCallBacks'))
        dictionary = self.keep(self.cf.CFDictionaryCreateMutable(None, 0, keys, values))
        for key, value in pairs.items():
            self.cf.CFDictionarySetValue(dictionary, self.constant(key), value)
        return dictionary

    def query(self, service, account, extra=None):
        return self.dictionary({
            'kSecClass': self.constant('kSecClassGenericPassword'),
            'kSecAttrService': self.string(service),
            'kSecAttrAccount': self.string(account),
            **(extra or {}),
        })


@contextmanager
def objects():
    cf, security = libraries()
    values = Objects(cf, security)
    try:
        yield values
    finally:
        for value in reversed(values.owned):
            cf.CFRelease(value)


def check(status):
    if status:
        raise ValueError(f'钥匙串访问失败（系统状态 {status}），请解锁钥匙串或检查访问授权')


def read(service, account):
    with objects() as values:
        query = values.query(service, account, {'kSecReturnData': values.constant('kCFBooleanTrue')})
        result = c.c_void_p()
        status = values.security.SecItemCopyMatching(query, c.byref(result))
        if status == MISSING:
            return None
        check(status)
        try:
            return c.string_at(values.cf.CFDataGetBytePtr(result), values.cf.CFDataGetLength(result)).decode('utf-8')
        finally:
            if result:
                values.cf.CFRelease(result)


def write(service, account, value):
    with objects() as values:
        data = values.data(value)
        query = values.query(service, account)
        attrs = values.dictionary({'kSecValueData': data})
        status = values.security.SecItemUpdate(query, attrs)
        if status == MISSING:
            status = values.security.SecItemAdd(values.query(service, account, {'kSecValueData': data}), None)
            if status == DUPLICATE:
                status = values.security.SecItemUpdate(query, attrs)
        check(status)


def delete(service, account):
    """Delete one explicitly named item (also used for integration-test cleanup)."""
    with objects() as values:
        status = values.security.SecItemDelete(values.query(service, account))
        if status != MISSING:
            check(status)
