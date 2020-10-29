#include <stdlib.h>
#include <stdint.h>
//#include <gram.h>

static inline uint32_t read32(const void *addr)
{
	return *(volatile uint32_t *)addr;
}

static inline void write32(void *addr, uint32_t value)
{
	*(volatile uint32_t *)addr = value;
}

struct led_regs {
    uint32_t value;
    uint32_t en;
};

struct uart_regs {
	//uint32_t divisor;
	uint32_t rx_data;
	uint32_t rx_rdy;
	//uint32_t rx_err;
	uint32_t tx_data;
	uint32_t tx_rdy;
	uint32_t zero0; // reserved
	uint32_t zero1; // reserved
	uint32_t ev_status;
	uint32_t ev_pending;
	uint32_t ev_enable;
};

struct prandom_regs {
    uint32_t rand;
    uint32_t free;
    uint32_t error;
};

void uart_write(char c)
{
	struct uart_regs *regs = 0x00005000;
	while (!read32(&regs->tx_rdy));
	write32(&regs->tx_data, c);
}

void uart_writestr(const char *c) {
	while (*c) {
		uart_write(*c);
		c++;
	}
}


void memcpy(void *dest, void *src, size_t n) {
   int i;
   //cast src and dest to char*
   char *src_char = (char *)src;
   char *dest_char = (char *)dest;
   for (i=0; i<n; i++)
	  dest_char[i] = src_char[i]; //copy contents byte by byte
}

void uart_writeuint32(uint32_t val) {
	const char lut[] = { '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F' };
	uint8_t *val_arr = &val;
	size_t i;

	for (i = 0; i < 4; i++) {
		uart_write(lut[(val_arr[3-i] >> 4) & 0xF]);
		uart_write(lut[val_arr[3-i] & 0xF]);
	}
}


void isr(void) {

}

union led_data {
    int raw;
    struct rgb_value {
        uint32_t r : 8;
        uint32_t g : 8;
        uint32_t b : 8;
    } structured;
};

void set_led_value(union led_data* C){
    const struct led_regs *led_controller = 0x00005200;
    write32(&led_controller->value,*(int*)C);
}

void set_led_state(int state){
    const struct led_regs *led_controller = 0x00005200;
    write32(&led_controller->en, state);
}

uint32_t get_rand(void) {
    const struct prandom_regs *rand_peripheral = 0x00005300;
    return read32(&rand_peripheral->rand);
}

int main(void) {
    union led_data colour;
    colour.raw = 0;
    uint8_t next = 1;
    uint32_t s = 1;
    while(1) { 
        set_led_state(s); 
        s = !s;
        if (!s) {
          /*  
            switch(next) {
                case 0:
                    next = 1;
                    uart_writestr("Red\n\r");
                    colour.structured.r = 255; colour.structured.g = 0; colour.structured.b = 0;
                    break;
                case 1:
                    next = 2;
                    uart_writestr("Green\n\r");
                    colour.structured.r = 0; colour.structured.g = 255; colour.structured.b = 0;
                    break;
                case 2:
                    next = 0;
                    uart_writestr("Blue\n\r");
                    colour.structured.r = 0; colour.structured.g = 0; colour.structured.b = 255;
                    break;
            }*/

            uart_writeuint32(colour.raw = get_rand());
            set_led_value(&colour);
            uart_writestr("\n\r");
        }
        
        for(int i = 5000000; i > 0; --i);
    }
    return 0;
}
