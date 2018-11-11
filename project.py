"""
Author: Vinh Truong
This file is an implementation of a virtual file system
to better understand the workings of operating systems
"""
import os
import sys
import pickle
from disk import disk
from openFileTable import oft

class fileSystem():

    def __init__(self):
        # 1 block is 64 Bytes (or) 16 integers
        # 64 blocks
        self.l_disk = disk()
        
        self.oft = oft()
        # Bitmap and 6 blocks for descriptors are reserved
        # block 0 is bitmap, blocks [1-6] is descriptors. 24 descriptors each 4 int is 4 descriptors per block
        # Each directory slot is 2 integers, with 24 descriptors, 24*2=48 int
        """
        DESCRIPTOR: 4 INTS, first: FILE LENGTH, 2-4: BLOCKS ALLOCATED
        DIRECTORY: 2 INTS, first: FILE NAME, second: DESCRIPTOR INDEX
        """
    
    ################################################################

    def _find_free_directory(self) -> int:
        """
        Finds a free directory slot. Directory will always (in this implementation)
        be stored in l_disk[7] to l_disk[9] inclusive

        p.s.: the first directory should be 0

        Return:
        An index of a free directory slot.
        """
        read = [0]*16
        for i in range(24):
            self.l_disk.read_block(7+(i//8), read)
            if read[((i%8)*2)+1] == -1:
                return i
        return -1
    
    def _find_free_descriptor(self) -> int:
        """
        Finds a free descriptor slot. All descriptors are in blocks 1-6 inclusive
        (so l_disk[1] to l_disk[6] inclusive), and each descriptor length is 4 int,
        making one descriptor == 1/4th of a block

        Return:
        the index of a free descriptor slot
        """
        descriptors = self.l_disk.read_descriptors()
        for i in range(len(descriptors)):
            if descriptors[i][0] == -1:
                return i
            
        return -1
   
    def _find_free_block(self) -> int:
        """
        Finds a free block by searching through the bitmap

        Return:
        Block index of a free block
        """
        free = 0
        second = False
        index = 32
        read = [0]*16
        self.l_disk.read_block(0, read)
        for i in range(31, -1, -1):
            bit = 2**i
            if read[0] & bit == 0:
                free = bit
                break
            if read[1] & bit == 0:
                free = bit
                second = True
                break
        
        if free == 0:
            print("NO THING LEFT; METHOD _find_free in fileSystem obj")
            return -1

        while free > 0:
            free //= 2
            index -= 1
        
        if second:
            index += 32
        
        return index
    
    def _get_file_length(self, descriptor_index) -> int:
        """
        Pass in the index of a descriptor to return
        the corresponding file length

        Return:
        int - length of corresponding file
        """
        descs = self.l_disk.read_descriptors()
        return descs[descriptor_index][0]
    ################################################################
    
    def __read_block(self, index: int) -> bool:
        """
        Creates a list and returns the info at
        ldisk[index]
        """
        read = [0]*16
        self.l_disk.read_block(index, read)
        return read

    def _add_block_to_descriptor(self, desc_index: int, block_index: int):
        """
        Adds a block to the descriptor
        """
        descriptor = self.l_disk.read_descriptors()[desc_index]
        for i in range(1,4):
            if descriptor[i] == -1:
                descriptor[i] = block_index
                break
        else:
            return False
        self._write_to_descriptor(desc_index, descriptor[0], descriptor[1:])

        bitmap = [0]*16
        self.l_disk.read_block(0, bitmap)
        if block_index+7 < 32:
            bitmap[0] = bitmap[0] | 2**(31-(block_index+7))
        elif block_index+7 < 64:
            bitmap[1] = bitmap[1] | 2**(63-(block_index+7))
        
        self.l_disk.write_block(0, bitmap)
        
        return True

    def _write_to_descriptor(self, index: int, file_length: int, used_blocks:list):
        """
        Writes the file_length and block_numbers to the ldisk given the
        index in relation of descriptors
        """
        block_num = 1 + (index//4)
        block_index = (index%4)*4
        read = self.__read_block(block_num)

        buf = [file_length]
        buf.extend(used_blocks)
        while len(buf) < 4:
            buf.append(-1)

        read[block_index:block_index+4] = buf
        self.l_disk.write_block(block_num, read)
    
    def _write_to_directory(self, index:int, file_name: str, descriptor_index: int):
        """
        Writes the file_name and descriptor_index to the ldisk given the
        index in relation of directory slots

        note: directory contents are stored in blocks (0+7), (1+7), (2+7)

        16 int per block, 8 dir slots per block
        """
        if len(file_name) > 4 or len(file_name) == 0:
            print("NOT A VALID FILE")

        block_num = 7 + (index//8)
        block_index = (index%8)*2
        read = self.__read_block(block_num)

        char_to_name = 0
        for c in file_name:
            char_to_name = char_to_name << 8
            char_to_name += ord(c)

        buf = [char_to_name]
        buf.append(descriptor_index)

        read[block_index:block_index+2] = buf
        self.l_disk.write_block(block_num, read)

    def _delete_descriptor(self, descriptor_index: int) -> [int]:
        """
        Deletes the descriptor at given descriptor index

        Return:
        list of allocated block indexes
        """
        block_num = 1 + (descriptor_index//4)
        block_index = (descriptor_index%4)*4
        read = self.__read_block(block_num)
        allocated = []
        if read[block_index+1] != -1:
            allocated.append(read[block_index+1])
        if read[block_index+2] != -1:
            allocated.append(read[block_index+2])
        if read[block_index+3] != -1:
            allocated.append(read[block_index+3])

        read[block_index:block_index+4] = [-1, -1, -1, -1]
        self.l_disk.write_block(block_num, read)

        return allocated

    def _delete_directory(self, directory_index: int):
        """
        Deletes the directory. does NOT delete the associated
        descriptor
        """
        block_num = 7 + (directory_index//8)
        block_index = (directory_index%8)*2
        read = self.__read_block(block_num)

        read[block_index:block_index+2] = [-1, -1]
        self.l_disk.write_block(block_num, read)

    def _increment_oft_pos(self, index:int) -> bool:
        """
        Increments the current_pos of an entry of the oft at index

        Return:
        bool - True if increment was successful, else False
        """
        # print(self.oft.current_pos[index])
        self.oft.current_pos[index] += 1
        if self.oft.current_pos[index]%64==0:
            # print((self.l_disk.descriptor_references(self.oft.index[index])))
            self._write_buffer_to_disk(index)
            # print((self.l_disk.descriptor_references(self.oft.index[index])))
            new_buffer = self.l_disk.read_from_descriptors(self.oft.index[index])
            if len(new_buffer)-1 < self.oft.current_pos[index]//64:
                return False
            else:
                self.oft.buffer[index] = new_buffer[self.oft.current_pos[index]//64]
        return True
              
    def _write_buffer_to_disk(self, index: int) -> None:
        """
        Writes given oft index buffer into disk using descriptor
        """
        block_index = self.l_disk.descriptor_references(self.oft.index[index])[self.oft.current_pos[index]//64-1]
        if block_index == -1:
            self._add_block_to_descriptor(self.oft.index[index], self._find_free_block()-7)
            block_index = self.l_disk.descriptor_references(self.oft.index[index])[self.oft.current_pos[index]//64-1]
        self.l_disk.write_block(block_index+7, self.oft.buffer[index])
        # print(self.l_disk.read_descriptors())
        # print(self.l_disk.read_from_descriptors(self.oft.index[index]))

    def create(self, name:str) -> bool:
        """
        Finds a free descriptor and directory slot and allocates
        for a new file.

        Return:
        bool - True if file is created, else False
        """
        descriptor_index = self._find_free_descriptor()
        directory_index = self._find_free_directory()

        entries = self.l_disk.read_directory()
        char_to_int = 0
        for char in name:
            char_to_int = char_to_int << 8
            char_to_int += ord(char)
        for i in range(len(entries)):
            if char_to_int == entries[i][0]:
                return False

        if descriptor_index == -1 or directory_index == -1:
            return False
        
        self._write_to_descriptor(descriptor_index, 0, [])
        self._write_to_directory(directory_index, name, descriptor_index)

        return True
        
    def destroy(self, name:str) -> bool:
        """
        Destory the file with given name

        Return
        bool - True if file is destroyed, else False
        """
        entries = self.l_disk.read_directory()
        char_to_int = 0
        descriptor_index_to_delete = None
        directory_index_to_delete = None

        for char in name:
            char_to_int = char_to_int << 8
            char_to_int += ord(char)
        for i in range(len(entries)):
            if char_to_int == entries[i][0]:
                descriptor_index_to_delete = entries[i][1]
                directory_index_to_delete = i
                break
        else:
            return False
        
        allocated = self._delete_descriptor(descriptor_index_to_delete)
        self._delete_directory(directory_index_to_delete)

        bitmap = [0]*16
        self.l_disk.read_block(0, bitmap)
        bitmap = bitmap[:2]
        for block in allocated:
            block += 7
            if block < 64:
                bitmap[0] -= 2 ** block
            else:
                bitmap[1] -= 2 ** (block-64)

        return True

    def op(self, name:str) -> int:
        """
        Opens a file and puts it in the open file table

        Return:
        int - index of the entry created in the oft
        """
        entries = self.l_disk.read_directory()
        char_to_int = 0
        descriptor_index = None

        for char in name:
            char_to_int = char_to_int << 8
            char_to_int += ord(char)
        for i in range(len(entries)):
            if char_to_int == entries[i][0]:
                descriptor_index = entries[i][1]
                break
        else:
            print("Nothing found???!?!??")
            return

        buffer = self.l_disk.read_from_descriptors(descriptor_index)
        if len(buffer) > 0:
            buffer = buffer[0]
        else:
            buffer = [0]*16
        return self.oft.new_entry(buffer, 
            descriptor_index, 
            self._get_file_length(descriptor_index))

    def close(self, index: int) -> bool:
        """
        Closes an open file in the oft

        Return:
        bool - True if the close was successful, else False
        """
        if index == 0:
            return True
        if self.oft.index[index] == -1:
            return False
        self._write_buffer_to_disk(index)
        self.oft.free_entry(index)
        return True

    def read(self, index: int, memory: str, count: int) -> str: ########## CHANGE LATER
        """
        Reads the data from the open file index into memory, count bytes
        or until end of file.

        Return:
        str - memory argument with file data inside
        """
        counter = 0
        while counter < count and self.oft.current_pos[index] < self.oft.file_len[index]:
            memory+= self.oft.read_byte(index)
            self._increment_oft_pos(index)
            if self.oft.current_pos[index] == self.oft.file_len[index]:
                break
            counter += 1
        return memory

    def write(self, index: int, memory:str, count: int) -> int: # Number of bytes written
        """
        Writes the str as bytes to the r/w buffer in the oft table

        Return:
        int - Number of bytes (chars) written to file
        """
        counter = 0
        for counter in range(count):
            self.oft.write_byte(index, memory)
            self._increment_oft_pos(index)
            if self.oft.current_pos[index] == 191:
                break
        if self.oft.file_len[index] < self.oft.current_pos[index]:
            self.oft.file_len[index] = self.oft.current_pos[index]
        return counter+1
            
    def lseek(self, index: int, pos: int) -> bool:
        """
        Sets the current_pos for a entry in the oft

        Return:
        bool - True if successful, else False
        """
        self._write_buffer_to_disk(index)
        if not pos < self.oft.file_len[index]:
            print("Invalid")
            return False

        buffer = self.l_disk.read_from_descriptors(self.oft.index[index])
        if len(buffer) > pos//64:
            buffer = buffer[pos//64]
        else:
            print("Invalid")
            return False
        self.oft.current_pos[index] = pos
        
        return True

    def directory(self) -> list: # returns the list of files
        """
        Returns the list of directories
        """
        slots = self.l_disk.read_directory()
        result = []
        for slot in slots:
            if slot[1] != -1:
                name = ""
                int_to_name = slot[0]
                while int_to_name != 0:
                    name += chr(int_to_name & 0b11111111)
                    int_to_name = int_to_name >> 8
                result.append(name[::-1])

        return result

    def initialize(self, fname = None): # restore ldisk from file.txt or create new
        if fname == None:
            self._write_to_descriptor(0, 48, [0, 1, 2])
            self.oft.new_entry([0]*16, 0, 192)
        else:
            with open(fname, "rb") as file:
                attributes = pickle.load(file)
                self.l_disk, self.oft = attributes

    def save(self, fname: str): # save ldisk to file.txt
        for i in range(4):
            self.close(i)
        with open(fname, "wb+") as file:
            attributes = (self.l_disk, self.oft)
            pickle.dump(attributes, file)

    
def main():
    y = fileSystem()
    cmd = [""]
    while cmd[0] != "q":
        process_command(y, input())

def read_file(fname):
    f_sys = fileSystem()
    output = "output.txt"
    with open(fname, "r") as f:
        with open(output, "w+") as out:
            for line in f.readlines():
                # print(line)
                out.write(process_command(f_sys, line.strip()))
                out.write("\n")
        
def process_command(f_sys, cmd) -> str:
    if cmd == "":
        return ""
    try:
        cmd = cmd.split()
        if cmd[0] == "cr":
            if (f_sys.create(cmd[1])):
                return ("{} created".format(cmd[1]))
            else:
                return "error"
        elif cmd[0] == "op":
            index = f_sys.op(cmd[1])
            return ("{} opened {}".format(cmd[1], index))
        elif cmd[0] == "wr":
            return ("{} bytes written".format(f_sys.write(int(cmd[1]), cmd[2], int(cmd[3]))))
        elif cmd[0] == "rd":
            temp = ""
            temp = f_sys.read(int(cmd[1]), temp, int(cmd[2]))
            return (temp)
        elif cmd[0] == "de":
            if f_sys.destroy(cmd[1]):
                return ("{} destroyed".format(cmd[1]))
            else:
                return "error"
        elif cmd[0] == "in":
            if len(cmd) == 1:
                f_sys.initialize()
                return ("disk initialized")
            else:
                f_sys.initialize(cmd[1])
                return ("disk restored")
        elif cmd[0] == "cl":
            if f_sys.close(int(cmd[1])):
                return ("{} closed".format(cmd[1]))
            else:
                return "error"
        elif cmd[0] == "sk":
            f_sys.lseek(int(cmd[1]), int(cmd[2]))
            return ("position is {}".format(cmd[2]))
        elif cmd[0] == "dr":
            result = ""
            for d in f_sys.directory():
                result += (d)
                result += " "
            result += "\n"
            return result
        elif cmd[0] == "sv":
            f_sys.save(cmd[1])
            return("disk saved")
    except:
        return("error")
        

if __name__ == "__main__":
    file = input("Please input the name of a file: ").strip()
    read_file(file)

    # x = fileSystem()
    # x.initialize()
    # x.create("foo")
    # x.op("foo")
    # x.close(1)
    # x.op("foo")
    # print("{} bytes written".format(x.write(1, "x", 60)))
    # print("{} bytes written".format(x.write(1, "y", 10)))
    # print("{} bytes written".format(x.write(1, "y", 10)))
    # print(x.lseek(1, 16))
    # temp = ""
    # temp = x.read(1, temp, 5)
    # print(temp)
    # x.close(1)
    # x.oft.print_table()
    # print(x.l_disk.read_descriptors())
    # print(x.directory())

    # print()
    # main()

    # x.create('1st')
    # x.destroy('1st')
    # x.create('2nd')
    # second = x.op('2nd')
    # print(x.l_disk.read_descriptors())
    # print()
    # x.close(second)
    # second = x.op('2nd')
    # x.oft.print_table()
    # x.write(second, "su", 3)
    # x.oft.print_table()
    # x.write(second, "p", 3)
    # x.close(second)
    # x.oft.print_table()



    # x.lseek(second, 0)
    # x.create("abcc")
    # x.create("bcaa")
    # x.create("cbaa")
    # print("Reading all descriptors")
    # print(x.l_disk.read_descriptors())
    # print("Reading whole directory")
    # print(x.l_disk.read_directory())
    # x._write_to_descriptor(1, 7, [3, 4, 5])
    # read = []
    # x.l_disk.read_block(7,read)
    # print("reading block 7 (first block of directory)")
    # print(read)
    # print()
    # print("Finding free descriptor")
    # print(x._find_free_descriptor())
    # print("reading blocks listed in first descriptor (== directory blocks)")
    # print(x.l_disk.read_from_descriptors(0))
    # print("opening a file n shiiit")
    # first = x.op("abcc")
    # second = x.op("bcaa")
    # fourth = x.op("cbaa")
    # print(first)
    # print(x.oft.print_table())
    # x.close(second)
    # print(x.oft.print_table())
    # x.create("xd")
    # second = x.op("xd")
    # print(x.oft.print_table())
    # x._increment_oft_pos(0)
    # print(x.oft.print_table())
    # main()