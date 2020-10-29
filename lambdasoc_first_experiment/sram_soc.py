import argparse
import importlib

from nmigen import *
from nmigen_soc import wishbone

from lambdasoc.cpu.minerva import MinervaCPU
from lambdasoc.periph.intc import GenericInterruptController
#from lambdasoc.periph.serial import AsyncSerialPeripheral
from lambdasoc.periph.sram import SRAMPeripheral
from lambdasoc.periph.timer import TimerPeripheral
from lambdasoc.soc.cpu import CPUSoC

from luna.gateware.platform.orangecrab import OrangeCrabPlatformR0D2
from USB_serial import USBSerialPeripheral

from ledController import RGB_LED
from pseudoRandomPeriph import PseudoRandomPeripheral

#from generate_headers import HeaderGenerator

__all__ = ["SRAMSoC"]


class SRAMSoC(CPUSoC, Elaboratable):
    def __init__(self, *,platform, reset_addr, clk_freq,
                 rom_addr, rom_size,
                 ram_addr, ram_size,
                 uart_addr,
                 timer_addr, timer_width,
                 led_addr,
                 rand_addr):
        self._arbiter = wishbone.Arbiter(addr_width=30, data_width=32, granularity=8,
                                         features={"cti", "bte"})
        self._decoder = wishbone.Decoder(addr_width=30, data_width=32, granularity=8,
                                         features={"cti", "bte"})

        self.cpu = MinervaCPU(reset_address=reset_addr)
        self._arbiter.add(self.cpu.ibus)
        self._arbiter.add(self.cpu.dbus)

        self.rom = SRAMPeripheral(size=rom_size, writable=False)
        with open("firmware/main.bin", "rb") as f:
            words = iter(lambda: f.read(self.cpu.data_width // 8), b'')
            bios  = [int.from_bytes(w, self.cpu.byteorder) for w in words]
        self.rom.init = bios
        self._decoder.add(self.rom.bus, addr=rom_addr)

        self.ram = SRAMPeripheral(size=ram_size)
        self._decoder.add(self.ram.bus, addr=ram_addr) 

        self.usb0 = platform.request(platform.default_usb_connection)
        self.uart = USBSerialPeripheral(usb_interface=self.usb0)
        self._decoder.add(self.uart.bus, addr=uart_addr)

        self.timer = TimerPeripheral(width=timer_width)
        self._decoder.add(self.timer.bus, addr=timer_addr)

        self.status_led = RGB_LED()
        self._decoder.add(self.status_led.bus, addr=led_addr)

        self.prandom = PseudoRandomPeripheral()
        self._decoder.add(self.prandom.bus, addr=rand_addr)

        self.intc = GenericInterruptController(width=len(self.cpu.ip))
        self.intc.add_irq(self.timer.irq, 0)
        self.intc.add_irq(self.uart .irq, 1)

        self.memory_map = self._decoder.bus.memory_map

        self.clk_freq = clk_freq

    def elaborate(self, platform):
        m = Module()
        
        m.submodules.car = platform.clock_domain_generator()

        m.submodules.arbiter = self._arbiter
        m.submodules.cpu     = self.cpu

        m.submodules.decoder = self._decoder
        m.submodules.rom     = self.rom
        m.submodules.ram     = self.ram
        m.submodules.uart    = self.uart
        m.submodules.timer   = self.timer
        m.submodules.intc    = self.intc
       
        self.status_led.led_resource = platform.request('rgb_led', 0)
        m.submodules.status_led = self.status_led
        
        m.submodules.prandom = self.prandom

        m.d.comb += [
            self._arbiter.bus.connect(self._decoder.bus),
            self.cpu.ip.eq(self.intc.ip),
        ]

        return m


if __name__ == "__main__":
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument("platform", type=str,
            help="target platform (e.g. 'nmigen_boards.arty_a7.ArtyA7Platform')")
    parser.add_argument("--baudrate", type=int,
            default=9600,
            help="UART baudrate (default: 9600)")

    args = parser.parse_args()

    def get_platform(platform_name):
        module_name, class_name = platform_name.rsplit(".", 1)
        module = importlib.import_module(name=module_name)
        platform_class = getattr(module, class_name)
        return platform_class()

    platform = get_platform(args.platform)
    '''
    platform = OrangeCrabPlatformR0D2()
    
    soc = SRAMSoC(platform=platform,
         reset_addr=0x00000000, clk_freq=int(platform.default_clk_frequency),
           rom_addr=0x00000000, rom_size=0x4000,
           ram_addr=0x00004000, ram_size=0x1000,
          uart_addr=0x00005000,
         timer_addr=0x00005100, timer_width=32,
         led_addr  =0x00005200,
         rand_addr =0x00005300,
    )

    #hGen = HeaderGenerator(soc._decoder)
    #hGen.addPeripheral(soc.uart)
    #hGen.addPeripheral(soc.timer)
    #hGen.addPeripheral(soc.intc)

    #soc.build(do_build=True, do_init=True)
    platform.build(soc, do_program=True)
