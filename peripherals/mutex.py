from nmigen import *
from nmigen.lib.scheduler import RoundRobin
from lambdasoc.periph import Peripheral

from numpy import log2, ceil

__all__ = ["MutexPeripheral"]

class MutexPeripheral(Elaboratable):
    def __init__(self, nr_of_clients=2, name="mutex"):
        self._nr_of_clients = nr_of_clients
        self._rr            = RoundRobin(count=nr_of_clients) 
        
        self.interfaces = [Peripheral(name=f"{name}_i{i}") for i in range(nr_of_clients)]
        
        self._clients = []
        for p in self.interfaces:
            bank = p.csr_bank()
            take    = bank.csr(1, "r", name="take")
            give    = bank.csr(1, "w", name="give")
            take_ev = p.event(mode="rise", name="take_ev")
            self._clients.append((take, give, take_ev))

            p._bridge = p.bridge(data_width=32, granularity=8, alignment=2)
            p.bus     = p._bridge.bus
            p.irq     = p._bridge.irq

    def elaborate(self, platform):

        m = Module()
        m.submodules.rr = self._rr
        for p in self.interfaces:
            m.submodules += p._bridge
        
        holding = Signal(self._nr_of_clients)
        waiting = Signal(self._nr_of_clients)
        free = Signal(1)
        m.d.comb += [free.eq(~(holding.any())), 
                     self._rr.requests.eq(waiting)]

        for c in range(self._nr_of_clients):
            m.d.comb += [self._clients[c][0].r_data.eq(holding[c] | (free & self._clients[c][0].r_stb)) ]
            m.d.sync += self._clients[c][2].stb.eq(0)
            with m.If(self._clients[c][0].r_stb):
                with m.If(free):
                    m.d.sync += [holding[c].eq(1)]
                with m.Elif(~ holding[c]):
                    m.d.sync += [waiting[c].eq(1)]

            with m.Elif(self._clients[c][1].w_stb):
                m.d.sync += [holding[c].eq(~(self._clients[c][1].w_data)),
                             self._clients[c][2].stb.eq(0)]

            with m.Else():
                with m.If(free & self._rr.valid & (self._rr.grant == Const(c))):
                    m.d.sync += [holding[c].eq(1),
                                 waiting[c].eq(0),
                                 self._clients[c][2].stb.eq(1)]
                with m.Else():
                    m.d.sync += self._clients[c][2].stb.eq(0)
        return m
