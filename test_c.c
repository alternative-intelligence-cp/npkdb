#include <stdio.h>
extern "C" void npk_core_init(void);
extern "C" void* npk_core_alloc(unsigned long size);
int main() {
    npk_core_init();
    void* p = npk_core_alloc(8);
    printf("p = %p\n", p);
    return 0;
}
