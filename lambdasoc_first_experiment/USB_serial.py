from nmigen import *
from nmigen.lib.fifo import AsyncFIFO

#from nmigen_stdio.serial import AsyncSerial

from luna.full_devices   import USBSerialDevice
from lambdasoc.periph import *
from lambdasoc.periph.serial import AsyncSerialPeripheral


__all__ = ["USBSerialPeripheral"]


class USBSerialPeripheral(AsyncSerialPeripheral, Peripheral):
    """Asynchronous serial transceiver peripheral.

    See :class:`nmigen_stdio.serial.AsyncSerial` for details.

    CSR registers
    -------------
    divisor : read/write
        Clock divisor.
    rx_data : read-only
        Receiver data.
    rx_rdy : read-only
        Receiver ready. The receiver FIFO is non-empty.
    rx_err : read-only
        Receiver error flags. See :class:`nmigen_stdio.serial.AsyncSerialRX` for layout.
    tx_data : write-only
        Transmitter data.
    tx_rdy : read-only
        Transmitter ready. The transmitter FIFO is non-full.

    Events
    ------
    rx_rdy : level-triggered
        Receiver ready. The receiver FIFO is non-empty.
    rx_err : edge-triggered (rising)
        Receiver error. Error cause is available in the ``rx_err`` register.
    tx_mty : edge-triggered (rising)
        Transmitter empty. The transmitter FIFO is empty.

    Parameters
    ----------
    rx_depth : int
        Depth of the receiver FIFO.
    tx_depth : int
        Depth of the transmitter FIFO.
    divisor : int
        Clock divisor reset value. Should be set to ``int(clk_frequency // baudrate)``.
    divisor_bits : int
        Optional. Clock divisor width. If omitted, ``bits_for(divisor)`` is used instead.
    data_bits : int
        Data width.
    parity : ``"none"``, ``"mark"``, ``"space"``, ``"even"``, ``"odd"``
        Parity mode.
    pins : :class:`Record`
        Optional. UART pins. See :class:`nmigen_boards.resources.UARTResource`.

    Attributes
    ----------
    bus : :class:`nmigen_soc.wishbone.Interface`
        Wishbone bus interface.
    irq : :class:`IRQLine`
        Interrupt request line.
    """
    def __init__(self, usb_interface, *, rx_depth=16, tx_depth=16, **kwargs):
        Peripheral.__init__(self)

        self._phy       = USBSerialDevice(bus=usb_interface, idVendor=0x16d0, idProduct=0x0f3b, manufacturer_string="lambdasoc")
        self._rx_fifo   = AsyncFIFO(width=self._phy.rx.payload.width, depth=rx_depth, r_domain="sync", w_domain="usb")
        self._tx_fifo   = AsyncFIFO(width=self._phy.tx.payload.width, depth=tx_depth, r_domain="usb", w_domain="sync")

        bank            = self.csr_bank()
        self._rx_data   = bank.csr(self._phy.rx.payload.width, "r")
        self._rx_rdy    = bank.csr(1, "r")
        #self._rx_err    = bank.csr(len(self._phy.rx.err),   "r")
        self._tx_data   = bank.csr(self._phy.tx.payload.width, "w")
        self._tx_rdy    = bank.csr(1, "r")

        self._rx_rdy_ev = self.event(mode="level")
        #self._rx_err_ev = self.event(mode="rise")
        self._tx_mty_ev = self.event(mode="rise")

        self._bridge    = self.bridge(data_width=32, granularity=8, alignment=2)
        self.bus        = self._bridge.bus
        self.irq        = self._bridge.irq

    def elaborate(self, platform):
        m = Module()
        m.submodules.bridge  = self._bridge

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
