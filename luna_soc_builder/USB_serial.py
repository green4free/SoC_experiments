from nmigen import *
from nmigen.lib.fifo import AsyncFIFO

from luna.full_devices   import USBSerialDevice
from lambdasoc.periph import *



__all__ = ["USBSerialPeripheral"]

#This was designed to replace the AsyncSerialPeripheral from lambdasoc

class USBSerialPeripheral(Peripheral, Elaboratable):
    def __init__(self, *, usb_interface = None, rx_depth=16, tx_depth=16, **kwargs):
        super().__init__()
        
        if usb_interface is None:
            self._phy = None
        else:
            self._phy = USBSerialDevice(bus=usb_interface, idVendor=0x16d0, idProduct=0x0f3b, manufacturer_string="lambdasoc")
        self._rx_fifo   = AsyncFIFO(width=8, depth=rx_depth, r_domain="sync", w_domain="usb")
        self._tx_fifo   = AsyncFIFO(width=8, depth=tx_depth, r_domain="usb", w_domain="sync")

        bank            = self.csr_bank()
        self._rx_data   = bank.csr(8, "r")
        self._rx_rdy    = bank.csr(1, "r")
        #self._rx_err    = bank.csr(len(self._phy.rx.err),   "r")
        self._tx_data   = bank.csr(8, "w")
        self._tx_rdy    = bank.csr(1, "r")

        self._rx_rdy_ev = self.event(mode="level")
        #self._rx_err_ev = self.event(mode="rise")
        self._tx_mty_ev = self.event(mode="rise")

        self._bridge    = self.bridge(data_width=32, granularity=8, alignment=2)
        self.bus        = self._bridge.bus
        self.irq        = self._bridge.irq

    def set_usb_interface(self, usb_interface):
        self._phy = USBSerialDevice(bus=usb_interface, idVendor=0x16d0, idProduct=0x0f3b, manufacturer_string="lambdasoc")

    def elaborate(self, platform):
        m = Module()
        m.submodules.bridge  = self._bridge
        assert(not self._phy is None)
        m.submodules.phy     = self._phy
        m.submodules.rx_fifo = self._rx_fifo
        m.submodules.tx_fifo = self._tx_fifo

        '''
        m.d.comb += self._divisor.r_data.eq(self._phy.divisor)
        with m.If(self._divisor.w_stb):
            m.d.sync += self._phy.divisor.eq(self._divisor.w_data)
        '''
        m.d.comb += [
            self._rx_data.r_data.eq(self._rx_fifo.r_data),
            self._rx_fifo.r_en.eq(self._rx_data.r_stb),
            self._rx_rdy.r_data.eq(self._rx_fifo.r_rdy),

            self._rx_fifo.w_data.eq(self._phy.rx.payload),
            self._rx_fifo.w_en.eq(self._phy.rx.valid),
            self._phy.rx.ready.eq(self._rx_fifo.w_rdy),
            #self._rx_err.r_data.eq(self._phy.rx.err),

            self._tx_fifo.w_en.eq(self._tx_data.w_stb),
            self._tx_fifo.w_data.eq(self._tx_data.w_data),
            self._tx_rdy.r_data.eq(self._tx_fifo.w_rdy),

            self._phy.tx.payload.eq(self._tx_fifo.r_data),
            self._phy.tx.valid.eq(self._tx_fifo.r_rdy),
            self._tx_fifo.r_en.eq(self._phy.tx.ready),

            self._rx_rdy_ev.stb.eq(self._rx_fifo.r_rdy),
            #self._rx_err_ev.stb.eq(self._phy.rx.err.any()),
            self._tx_mty_ev.stb.eq(~self._tx_fifo.r_rdy),

            self._phy.tx.first.eq(1),
            self._phy.tx.last.eq(1),
            self._phy.connect.eq(1)
        ]

        return m
