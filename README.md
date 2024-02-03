# Simple Compiler
A simple programming language frontend written in python using llvmlite.

# Getting Started
## Building a program
```
python main.py build test.txt
```

## Running a program (JIT Compilation)
```
python main.py run test.txt
```

## Writing a simple program
There are only void's and int's in this language so we can't print out "Hello, World!"
```c++
#include <iostream>

int main() {
    print(120);
    return 0;
}
```
