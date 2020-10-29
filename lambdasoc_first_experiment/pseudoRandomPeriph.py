from numpy import log2, ceil
from nmigen import *
#from nmigen.build import Resource
from lambdasoc.periph import *
from nmigen_boards.resources import *

class PseudoRandomPeripheral(Peripheral, Elaboratable):
    XNOR_TAPS = {3:[3,2], 4:[4,3], 5:[5,3], 6:[6,5], 7:[7,6], 8:[8,6,5,4], 9:[9,5], 10:[10,7], 11:[11,9], 12:[12,6,4,1], 13:[13,4,3,1], 14:[14,5,3,1],
                 15:[15,14], 16:[16,15,13,4], 17:[17,14], 18:[18,11], 19:[19,6,2,1], 20:[20,17], 21:[21,19], 22:[22,21], 23:[23,18], 24:[24,23,22,17],
                 25:[25,22], 26:[26,6,2,1], 27:[27,5,2,1], 28:[28,25], 29:[29,27], 30:[30,6,4,1], 31:[31,28], 32:[32,22,2,1], 33:[33,20], 34:[34,27,2,1],
                 35:[35,33], 36:[36,25], 37:[37,5,4,3,2,1], 38:[38,6,5,1], 39:[39,35], 40:[40,38,21,19], 41:[41,38], 42:[42,41,20,19], 43:[43,42,38,37],
                 44:[44,43,18,17], 45:[45,44,42,41], 46:[46,45,26,25], 47:[47,42], 48:[48,47,21,20], 49:[49,40], 50:[50,49,24,23], 51:[51,50,36,35],
                 52:[52,49], 53:[53,52,38,37], 54:[54,53,18,17], 55:[55,31], 56:[56,55,35,34], 57:[57,50], 58:[58,39], 59:[59,58,38,37], 60:[60,59],
                 61:[61,60,46,45], 62:[62,61,6,5], 63:[63,62], 64:[64,63,61,60]}

    def __init__(self,data_width=32):
        super().__init__()
        
        if data_width < 3 or data_width > 64:
            why = "big" if data_width > 64 else "small"
            raise ValueError(f"data_width must be in range [3,64], {data_width} is too {why}.")
        

        self.data_width = data_width
        
        self._taps = self.XNOR_TAPS[data_width]

        bank = self.csr_bank()
        self._rand  = bank.csr(data_width, "rw")
        self._free  = bank.csr(1, "w")
        self._error = bank.csr(1, "r")

        self._bridge    = self.bridge(data_width=32, granularity=8, alignment=2)
        self.bus        = self._bridge.bus

    def elaborate(self, platform):
        m = Module()

        def xnor_tree(arr):
            tmp = Signal()
            if len(arr) < 2:
                raise IndexError("The array of signals can't be shorter than two")
            elif len(arr) == 2:
                m.d.comb += tmp.eq(~(arr[0] ^ arr[1]))
            else:
                left  = arr[:len(arr)//2]
                right = arr[len(arr)//2:]
                m.d.comb += tmp.eq(~(xnor_tree(left) ^ xnor_tree(right)))
            return tmp
        
        free = Signal()
        LFSR = Signal(self.data_width)
        xnor_reduction = xnor_tree([LFSR[tap - 1] for tap in self._taps])

        m.submodules.bridge  = self._bridge
        
        with m.If(self._free.w_stb):
            m.d.sync += free.eq(self._free.w_data)
        
        with m.If(self._rand.w_stb):
            m.d.sync += LFSR.eq(self._rand.w_data) #Seed
        with m.Elif(free | self._rand.r_stb):
            m.d.sync += LFSR.eq(Cat(xnor_reduction,(LFSR << 1)[1:]))
        
        m.d.comb += [self._rand.r_data.eq(LFSR), self._error.r_data.eq(LFSR.all())]
        
        return m


