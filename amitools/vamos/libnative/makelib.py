from .makefuncs import MakeFuncs
from .initstruct import InitStruct
from amitools.vamos.atypes import Library
from amitools.vamos.machine.regs import *


class MakeLib(object):
  def __init__(self, machine, alloc):
    self.mem = machine.get_mem()
    self.alloc = alloc
    self.machine = machine

  def make_library(self, vectors_addr, init_struct_addr, init_func_addr,
                   pos_size, seglist_baddr, label_name=None, run_sp=None):
    """Exec's MakeLibrary

       return lib_base, mem_obj or None, None
    """
    neg_size, offsets = self._calc_neg_size(vectors_addr)
    neg_size = self._round_long(neg_size)
    pos_size = self._round_long(pos_size)
    size = neg_size + pos_size

    # allocate lib mem
    if label_name is None:
      label_name = "MakeLibrary"
    mobj = self.alloc.alloc_memory(label_name, size)
    addr = mobj.addr
    lib_base = addr + neg_size

    # init funcs
    mf = MakeFuncs(self.mem)
    if offsets:
      mf.make_functions(lib_base, vectors_addr+2, vectors_addr)
    else:
      mf.make_functions(lib_base, vectors_addr)

    # lib object and set neg/pos size
    lib = Library(self.mem, lib_base)
    lib.set_neg_size(neg_size)
    lib.set_pos_size(pos_size)

    # init struct?
    if init_struct_addr != 0:
      i = InitStruct(self.mem)
      i.init_struct(init_struct_addr, lib_base, 0)

    # init func?
    if init_func_addr != 0:
      set_regs = {
          REG_D0: lib_base,
          REG_A0: seglist_baddr,
          REG_A6: self.mem.r32(4)
      }
      get_regs = [REG_D0]
      # run machine and share current sp
      rs = self.machine.run(init_func_addr, sp=run_sp,
                            set_regs=set_regs, get_regs=get_regs,
                            name=label_name)
      lib_base = rs.regs[REG_D0]

    return lib_base, mobj

  def _round_long(self, v):
    rem = v & 3
    if rem > 0:
      v += 4 - rem
    return v

  def _calc_neg_size(self, vectors_addr):
    ptr = vectors_addr
    num_vec = 0
    # is it a word offset table?
    if self.mem.r16s(ptr) == -1:
      ptr += 2
      while True:
        off = self.mem.r16s(ptr)
        if off == -1:
          break
        ptr += 2
        num_vec += 1
      offsets = True
    # pointer table
    else:
      while True:
        fptr = self.mem.r32(ptr)
        if fptr == 0xffffffff:
          break
        ptr += 4
        num_vec += 1
      offsets = False
    # calc neg_size and round to long
    neg_size = num_vec * 6
    return neg_size, offsets
