#!/usr/bin/env python
#
# This file is part of LUNA.
#
# Copyright (c) 2020 Great Scott Gadgets <info@greatscottgadgets.com>
# SPDX-License-Identifier: BSD-3-Clause

from nmigen                       import Elaboratable, Module, Cat
from nmigen.hdl.rec               import Record

from lambdasoc.periph             import Peripheral
from lambdasoc.periph.serial      import AsyncSerialPeripheral
from lambdasoc.periph.timer       import TimerPeripheral

from luna                         import top_level_cli
from luna.gateware.soc            import SimpleSoC
from luna.gateware.interface.uart import UARTTransmitterPeripheral

from luna.gateware.platform.orangecrab import OrangeCrabPlatformR0D2
from USB_serial import USBSerialPeripheral

from ledController import RGB_LED
from pseudoRandomPeriph import PseudoRandomPeripheral

class Top(Elaboratable):

    def __init__(self):
        self.soc = soc = SimpleSoC(clock_frequency=int(48e6))

        soc.add_rom("main.bin", size=0x1000)
        soc.add_ram(0x1000)
        
        self.USB_serial = USB_serial = USBSerialPeripheral()
        soc.add_peripheral(USB_serial)

        self.timer = timer = TimerPeripheral(24)
        soc.add_peripheral(timer)

        self.status_led = status_led = RGB_LED()
        soc.add_peripheral(status_led)

        self.prandom = prandom = PseudoRandomPeripheral()
        soc.add_peripheral(prandom)
    
    def elaborate(self, platform):
        m = Module()

        m.submodules.car = platform.clock_domain_generator()
        self.USB_serial.set_usb_interface(platform.request(platform.default_usb_connection))
        self.status_led.led_resource = platform.request('rgb_led', 0)
        m.submodules.soc = self.soc

        return m

if __name__ == "__main__":
    design = Top()
    top_level_cli(design, cli_soc=design.soc)
