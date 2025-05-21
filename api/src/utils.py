import re
import random
from functools import reduce
from collections import deque


def generate_ean(total_value: float, base: str, rule:str = "999....NNNDD") -> str:
    def checksum(ean: str) -> int:
        sum = lambda x, y: int(x) + int(y)
        evensum = reduce(sum, ean[::2])
        oddsum = reduce(sum, ean[1::2])
        return (10 - ((evensum + oddsum * 3) % 10)) % 10
    
    INT_SIZE = len(re.findall(r"N", rule))
    FLT_SIZE = len(re.findall(r"D", rule))

    values = deque(list(base))
    while len(values) > 0:
        index = rule.index(".")
        value = values.popleft()
        rule = rule[:index] + str(value) + rule[index + 1:]

    int_buffer_size = INT_SIZE - len(str(int(total_value)))
    barcode_value = "0"*int_buffer_size + re.sub(r"\.", "", str(total_value))
    flt_buffer_size = INT_SIZE + FLT_SIZE - len(barcode_value)
    barcode_value = barcode_value + "0"*flt_buffer_size

    ean = re.sub(r"N{1,3}D{1,2}", barcode_value, rule)
    return ean + str(checksum(ean))
