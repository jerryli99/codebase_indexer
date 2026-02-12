#include <stdio.h>
#include "utils.h"
#include "math_ops.h"

int main(int argc, char *argv[]) {
    printf("Starting C program...\n");
    
    // Test math operations
    int a = 10, b = 5;
    int sum = add(a, b);
    int product = multiply(a, b);
    
    printf("Sum: %d\n", sum);
    printf("Product: %d\n", product);
    
    // Test utility functions
    print_array((int[]){1, 2, 3, 4, 5}, 5);
    
    int max = find_max((int[]){10, 25, 3, 47, 12}, 5);
    printf("Max value: %d\n", max);
    
    return 0;
}
