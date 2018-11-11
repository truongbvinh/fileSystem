"""
Open file table (OFT) to be used in project.py
Author: Vinh Truong
"""
from disk import disk

class oft():

    def __init__(self):
        self.buffer = [[0]*16 for _ in range(4)]
        self.current_pos = [-1]*4
        self.index = [-1]*4
        self.file_len = [-1]*4
        self.masks = [255 << 24, 255 << 16, 255 << 8, 255]
        self.neg_masks = [self.masks[1]+self.masks[2]+self.masks[3],
                        self.masks[0]+self.masks[2]+self.masks[3],
                        self.masks[0]+self.masks[1]+self.masks[3],
                        self.masks[0]+self.masks[1]+self.masks[2]]
    
    def new_entry(self, buffer, i, file) -> int:
        """
        Given the buffer, position, descriptor index and file length,
        inserts a new entry into the oft

        Return:
        int - index of the new entry in the oft
        """
        result = -1
        for j in range(4):
            # I check the index of file descriptor, but any
            # of the attrubutes can be checked.
            if self.current_pos[j] == -1:
                result = j
                break
        else:
            print("No space in oft thingy!!?!??")

        if buffer != None:
            self.buffer[result] = buffer
        self.current_pos[result] = 0
        self.index[result] = i
        self.file_len[result] = file

        return result
    
    def free_entry(self, index: int):
        self.buffer[index] = [0]*16
        self.current_pos[index] = -1
        self.index[index] = -1
        self.file_len[index] = -1

    def read_byte(self, index: int) -> chr:
        """
        Reads a byte from the buffer at the current_pos

        Return:
        chr - character at given byte index
        """
        int_coord = (self.current_pos[index]%64)//4
        byte_coord = (self.current_pos[index]%64)%4
        result = self.buffer[index][int_coord] & self.masks[byte_coord]
        result = result >> 8*(3-byte_coord)
        return chr(result)
    
    def write_byte(self, index: int, byte: chr):
        """
        Takes in a byte and writes to the r/w buffer
        """
        int_coord = (self.current_pos[index]%64)//4
        byte_coord = (self.current_pos[index]%64)%4
        shifted = ord(byte) << 8*(3-byte_coord)
        # print("{0:b}, {0:b}".format(shifted, ord(byte)))
        self.buffer[index][int_coord] = (self.buffer[index][int_coord] & self.neg_masks[byte_coord]) | shifted
        

    def print_table(self):
        for i in range(4):
            print("{}".format(self.buffer[i]), end=" ")
            print("{} {} {}".format(self.current_pos[i], self.index[i], self.file_len[i]))