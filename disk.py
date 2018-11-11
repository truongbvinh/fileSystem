"""
Author: Vinh Truong
This file is an l_disk implementation to be used in the 
virtual file system
"""

class disk():

    def __init__(self):
        self.ldisk = [[-1]*16 for _ in range(64)] 
        self.ldisk[0] = [0]*16
        self.ldisk[0][0] = 2**31 + 2**30 + 2**29 + 2**28 + 2**27 + 2**26 + 2**25

        # self.ldisk[1][]
    
    def read_block(self, i: int, store: [int]) -> [int]:
        """
        Reads from block index i and copies the block into store
        """
        store[:] = self.ldisk[i]
        return store

    def write_block(self, i: int, store: [int]) -> None:
        """
        Writes to a block index i from the store
        """
        self.ldisk[i][:] = store
    
    def descriptor_references(self, descriptor_index: int) -> [int]:
        """
        Takes in an index for a descriptor

        Return
        [int] - a list of integers of the blocks that the descriptor points to
        """
        return self.read_descriptors()[descriptor_index][1:]

    def read_descriptors(self) -> [[int]]:
        """
        Returns a list of lists of ints, where each nested
        list is a slot for a descriptor.
        """
        temp = [[0]*16 for _ in range(6)]
        for block in range(len(temp)):
            self.read_block(block+1, temp[block])
        
        result = []
        for block in temp:
            result.append(block[:4])
            result.append(block[4:8])
            result.append(block[8:12])
            result.append(block[12:16])
        return result
    
    def read_from_descriptors(self, descriptor_index: int) -> [[int]]:
        """
        Takes in an index for a descriptor

        Return:
        [[int]] - a list of list(s) of ints, which are the blocks listed
        in the descriptor
        """
        result = []
        for block_index in self.descriptor_references(descriptor_index):
            if block_index != -1:
                temp = []
                self.read_block(block_index+7, temp)
                result.append(temp)
        return result
        
    def read_directory(self) -> [[int]]:
        """
        Returns a list of Lists of ints, where each nested
        list is a slot for a directory entry
        """
        d_blocks = self.read_from_descriptors(0)
        result = []
        for block in d_blocks:
            for i in range(0,8,2):
                result.append(block[i:i+2])
        return result

if __name__ == "__main__":
    x = disk()
    read = [0]*16
    x.read_block(0, read)
    print(read)
    print(x.ldisk[0])
    print()
    print(x.read_descriptors())
    print(bytes(x.ldisk[0][0]))