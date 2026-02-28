import random

# make binary file with n random bytes
fname = "f.bin"
num_bytes = 0x100 #256
with open(fname, "wb") as f:
    for b in range(num_bytes):
        f.write(bytes([b]))

# load and read to exhaustion
# with open(fname, "rb") as f:
#     stuff = []
#     while b := f.read(1):
#         try:
#             stuff.append(b.decode())
#         except Exception as e:
#             pass
#     print("".join(stuff))

with open(fname, "rb") as f:
    stuff = f.read()
    for s in stuff:
        print(s)