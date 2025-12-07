import sys
from parser import Parser
from interpreter import Interpreter


def main():
    # python -m main put_do_ulaznog_fajla
    if len(sys.argv) != 2:
        print("Usage: python main.py <program-file>")
        return

    filename = sys.argv[1]
    try:
        with open(filename, "r", encoding="utf-8") as f:
            program = f.read()
    except FileNotFoundError:
        print(f"Error: file '{filename}' not found.")
        return

    parser = Parser(program)
    classes, statements = parser.parse()

    interp = Interpreter(classes, statements)
    interp.run()

    interp.print_classes()
    interp.print_instances()


if __name__ == "__main__":
    main()
