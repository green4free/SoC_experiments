from nmigen import *
#from nmigen.build import Resource
from lambdasoc.periph import *
from nmigen_boards.resources import *

class PWM(Elaboratable):
    def __init__(self, width):
        self.width = width
        self.pwm = Signal()
        self.dutyCycle = Signal(width, reset=0)
        self.counter = Signal(width, reset=0)

    def elaborate(self, platform):
        m = Module()
        m.d.sync += self.counter.eq(self.counter + 1)
        m.d.comb += self.pwm.eq(self.counter < self.dutyCycle)
        return m

class RGB_LED(Peripheral, Elaboratable):
    def __init__(self,channel_width=8,rgb_led=None):
        super().__init__()
        self._channel_width=channel_width
        self._rgb_led = rgb_led

        self._pwm_channels = [PWM(channel_width) for _ in range(3)]

        bank = self.csr_bank()
        self._value = bank.csr(channel_width * 3, "w")
        self._en = bank.csr(1, "w")

        self._bridge    = self.bridge(data_width=32, granularity=8, alignment=2)
        self.bus        = self._bridge.bus

    @property
    def led_resource(self):
        if self._rgb_led is None:
            raise NotImplementedError("LED resource for {!r} is not set yet.".format(self))
        return self._rgb_led

    @led_resource.setter
    def led_resource(self, rgb_led):
        #I don't get this isInstance thing to work, I don't think that the class of a RGBLEDResource is static.
        #Just be careful...
        #if not isinstance(rgb_led, type(RGBLEDResource(0,r="fakePin", g="fakePin", b="fakePin"))):
            #raise TypeError("LED resource must be a RGBLEDResource from nMigen-boards, not {!r}".format(rgb_led))
        self._rgb_led = rgb_led

    def elaborate(self, platform):
        if self._rgb_led is None:
            raise NotImplementedError("LED resource for {!r} is not set yet.".format(self))
        m = Module()
        
        en = Signal()

        m.submodules.bridge  = self._bridge
        for i in range(3):
            m.submodules += self._pwm_channels[i]

        with m.If(self._en.w_stb):
            m.d.sync += en.eq(self._en.w_data)

        with m.If(self._value.w_stb):
            m.d.sync += [self._pwm_channels[0].dutyCycle.eq(self._value.w_data[0:self._channel_width]), 
                         self._pwm_channels[1].dutyCycle.eq(self._value.w_data[self._channel_width:2*self._channel_width]), 
                         self._pwm_channels[2].dutyCycle.eq(self._value.w_data[2*self._channel_width:3*self._channel_width])] 

        m.d.comb += [
                self._rgb_led.r.o.eq(Mux(en, self._pwm_channels[0].pwm, 0)),
                self._rgb_led.g.o.eq(Mux(en, self._pwm_channels[1].pwm, 0)),
                self._rgb_led.b.o.eq(Mux(en, self._pwm_channels[2].pwm, 0))
                ]
        return m


