import collections
import pickle
import os


class LRUCache:
    def __init__(self, capacity=100, file=None):
        self.capacity = capacity
        self.file = file
        if file and os.path.isfile(file):
            pkl_file = open(file, "rb")
            self.cache = pickle.load(pkl_file)
            pkl_file.close()
        else:
            self.cache = collections.OrderedDict()

    def get(self, key):
        try:
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
        except KeyError:
            return None

    def set(self, key, value):
        try:
            self.cache.pop(key)
        except KeyError:
            if self.capacity > 0:
                while len(self.cache) >= self.capacity:
                    self.cache.popitem(last=False)
        self.cache[key] = value

    def save(self):
        if self.file:
            dir = os.path.dirname(self.file)
            if not os.path.exists(dir):
                os.makedirs(dir)
            output = open(self.file, "wb")
            pickle.dump(self.cache, output)
            output.close()
