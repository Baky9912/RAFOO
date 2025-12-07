# RAFOO

RAF Object Oriented is a small educational language that demonstrates basic OOP ideas using classes, inheritance, symbols, instances and static method dispatch. It supports object references, casting, and cloning. The language includes basic semantic analysis.
RAF_OO keeps the rules simple so the core concepts of objects and types are easy to understand.

## Run

```
python main.py primeri/osnovno.oop
```

## Example

```
CLASS B
    base = None
    fields = [a]
    methods = {
        show -> [a]
    }

CLASS A
    base = B
    fields = [x]
    methods = {
        show -> [a, x]
    }

let a = new A(1, 2)

call a.show

let b = cast<B> a
call b.show

b.a = 50

call a.show
call b.show

let c = clone b
call c.show

c.a = 9

call c.show
call a.show
```
