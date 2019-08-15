import struct
from .AllocatedArea import AllocatedArea, AllocatedAreaMagic


class X86Context:
    def __init__(self, infile):
        self.register_values = list()
        for i in range(0, 7):
            reg_val = struct.unpack_from('Q', infile.read(struct.calcsize("Q")))[0]
            self.register_values.append(reg_val)
        self.return_value = struct.unpack_from('c', infile.read(struct.calcsize('c')))[0]
        self.allocated_areas = list()
        for idx in range(0, len(self.register_values)):
            reg = self.register_values[idx]
            if reg == AllocatedAreaMagic and idx < len(self.register_values) - 1:
                self.allocated_areas.append(AllocatedArea(infile))

        syscall_count = struct.unpack_from('N', infile.read(struct.calcsize('N')))[0]
        self.syscalls = list()
        for idx in range(0, syscall_count):
            self.syscalls.append(struct.unpack_from('Q', infile.read(struct.calcsize('Q')))[0])
        self.syscalls.sort()

    def __hash__(self):
        hash_sum = 0

        for reg in self.register_values:
            hash_sum = hash((hash_sum, reg))

        for area in self.allocated_areas:
            hash_sum = hash((hash_sum, area))

        if hasattr(self, 'syscalls'):
            for syscall in self.syscalls:
                hash_sum = hash((hash_sum, syscall))

        return hash_sum

    def __eq__(self, other):
        return hash(self) == hash(other)

    def write_bin(self, infile):
        for reg in self.register_values:
            infile.write(struct.pack('Q', reg))
        infile.write(struct.pack('c', self.return_value))

        for subarea in self.allocated_areas:
            subarea.write_bin(infile)

        if hasattr(self, 'syscalls'):
            infile.write(struct.pack("N", len(self.syscalls)))
            for syscall_number in self.syscalls:
                infile.write(struct.pack('Q', syscall_number))
        else:
            infile.write(struct.pack('N', 0))

    def size_in_bytes(self):
        total_size = 0
        for reg in self.register_values:
            total_size += struct.calcsize('Q')
        total_size += struct.calcsize('c')

        for subarea in self.allocated_areas:
            subarea_size = subarea.size_in_bytes()
            print("subarea_size: %d" % (subarea_size))
            total_size += subarea_size

        total_size += struct.calcsize('N')
        if hasattr(self, 'syscalls'):
            for syscall_number in self.syscalls:
                total_size += struct.calcsize('Q')

        return total_size
