#include "resources.h"


void uart_write(char c)
{
	for(uint8_t trys = 0; !USB_serial_tx_rdy_read(); ++trys) if (trys > 50) return;
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
        uart_writestr("  Hello World!\n\r");
	}

    if(mutex_i0_interrupt_pending()) {
        mutex_i0_ev_pending_write(mutex_i0_ev_pending_read()); 
        uart_writestr("Nr0:s turn\n\r");
    } else if(mutex_i1_interrupt_pending()) {
        mutex_i1_ev_pending_write(mutex_i1_ev_pending_read());
        uart_writestr("Nr1:s turn\n\r");
    } else if(mutex_i2_interrupt_pending()) {
        mutex_i2_ev_pending_write(mutex_i2_ev_pending_read());
        uart_writestr("Nr2:s turn\n\r");
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
    uint32_t loop = 7;
    prandom_free_write(1);
    status_led_en_write(1);
    //timer_reload_write(0xA00000);
	//timer_en_write(1);
	//timer_ev_enable_write(1);
    mutex_i0_ev_enable_write(1);
    mutex_i1_ev_enable_write(1);
    mutex_i2_ev_enable_write(1);

    irq_setie(1);
	//timer_interrupt_enable();
    mutex_i0_interrupt_enable();
    mutex_i1_interrupt_enable();
    mutex_i2_interrupt_enable();

    status_led_value_write(0x00ff00);
    for (volatile uint32_t cd = 0xffffff; cd != 0; --cd);
    uart_writestr("Starting\n\r");
    uint32_t rand;
    while(1) {
        rand = prandom_rand_read();
        switch((rand > 0x55555555) + (rand > 0xaaaaaaab)) {
            case 0:
                if (mutex_i0_take_read()) {
                    if (loop-- == 7 ) uart_writestr("M0 starting\n\r");
                    status_led_value_write(0xfcba03); 
                    for (uint32_t cd = 0x5ffff; cd != 0; --cd);     
                    if (loop == 0) {
                        uart_writestr("M0 done\n\r");
                        mutex_i0_give_write(1);
                        loop = 7;
                        status_led_value_write(0xffffff); 
                        for (volatile uint32_t cd = 0x2fffff; cd != 0; --cd);     
                    }    
                }
                break;

            case 1:
                if (mutex_i1_take_read()) {
                    if (loop-- == 7 ) uart_writestr("M1 starting\n\r");
                    status_led_value_write(0x09915b); 
                    for (uint32_t cd = 0x5ffff; cd != 0; --cd);     
                    if (loop == 0) {
                        uart_writestr("M1 done\n\r");
                        mutex_i1_give_write(1);
                        loop = 7;
                        status_led_value_write(0xffffff); 
                        for (volatile uint32_t cd = 0x2fffff; cd != 0; --cd);     
                    }    
                }
                break;

            case 2:
                if (mutex_i2_take_read()) {
                    if (loop-- == 7 ) uart_writestr("M2 starting\n\r");
                    status_led_value_write(0xf5425d); 
                    for (uint32_t cd = 0x5ffff; cd != 0; --cd);     
                    if (loop == 0) {
                        uart_writestr("M2 done\n\r");
                        mutex_i2_give_write(1);
                        loop = 7;
                        status_led_value_write(0xffffff); 
                        for (volatile uint32_t cd = 0x2fffff; cd != 0; --cd);     
                    }    
                }
                break;
        }
        for (volatile uint32_t cd = 0xfffff; cd != 0; --cd);     
        
    }
}
