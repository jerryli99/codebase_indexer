#include "math_ops.h"

int add(int a, int b) {
    return a + b;
}

int subtract(int a, int b) {
    return a - b;
}

int multiply(int a, int b) {
    int result = 0;
    for (int i = 0; i < b; i++) {
        result = add(result, a);
    }
    return result;
}

int divide(int a, int b) {
    if (b == 0) {
        return 0;  // Error case
    }
    return a / b;
}

int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return multiply(n, factorial(subtract(n, 1)));
}
