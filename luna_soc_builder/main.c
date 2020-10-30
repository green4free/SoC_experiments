#include "resources.h"

uint32_t rand_d;

void uart_write(char c)
{
	for(uint8_t trys = 0; !USB_serial_tx_rdy_read(); ++trys) if (trys > 5) return;
	USB_serial_tx_data_write(c);
}

void uart_writestr(char *c) {
	while (*c) {
		uart_write(*c);
		c++;
	}
}


void dispatch_isr(void)
{
    if(timer_interrupt_pending()) {
		timer_ev_pending_write(timer_ev_pending_read());
        uart_write(((uint8_t*)&rand_d)[0]);
        uart_write(((uint8_t*)&rand_d)[1]);
        uart_write(((uint8_t*)&rand_d)[2]);
        uart_write(((uint8_t*)&rand_d)[3]);
        uart_writestr("  Hello World!\n\r");
	}
}


union led_data {
    int raw;
    struct rgb_value {
        uint32_t r : 8;
        uint32_t g : 8;
        uint32_t b : 8;
    } structured;
};


int main(void) {  
    status_led_en_write(1); 

    timer_reload_write(0xA00000);
	timer_en_write(1);
	timer_ev_enable_write(1);

    irq_setie(1);
	timer_interrupt_enable();

    while(1) {
        for (uint32_t cd = 0xfffff; cd != 0; --cd);     
        status_led_value_write(rand_d = prandom_rand_read());
    }
}
