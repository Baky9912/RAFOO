# interpreter.py
# Interpreter koji izvršava naredbe, sa "view" tipom (cast) i deljenjem instanci.

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
from lang_types import ClassDef, Instance, is_int


@dataclass
class VarBinding:
    """
    Veza promenljive u okruženju.

    inst     - konkretan objekat (runtime instanca)
    view_cls - klasa kroz koju ga posmatramo (npr. cast<B> A)
               koristi se za pronalaženje metoda.
    """
    inst: Instance
    view_cls: ClassDef


class Interpreter:
    def __init__(self, classes: Dict[str, ClassDef], statements: List[str]):
        self.classes = classes
        self.statements = statements
        # env: ime promenljive -> (instanca, view klasa)
        self.env: Dict[str, VarBinding] = {}

    def run(self) -> None:
        """
        Izvršava sve naredbe redom.
        """
        for stmt in self.statements:
            self._exec_statement(stmt)

    def _exec_statement(self, stmt: str) -> None:
        """
        Prepoznaje tip naredbe i delegira izvršavanje.
        Uklanja komentare koji počinju sa ';'.
        """
        # ukloni krajnji komentar posle ';'
        stmt = stmt.split(";", 1)[0].strip()
        if not stmt:
            return

        if stmt.startswith("let "):
            self._exec_let(stmt)
            return

        if "." in stmt and "=" in stmt and not stmt.startswith("call "):
            self._exec_field_assign(stmt)
            return

        if stmt.startswith("call "):
            self._exec_call(stmt)
            return

        if " is " in stmt:
            self._exec_is(stmt)
            return

        raise ValueError(f"Unknown statement: {stmt}")

    # ------------- let naredbe -------------

    def _exec_let(self, stmt: str) -> None:
        """
        Obrada naredbe 'let ime = izraz'.
        Izrazi koje podržavamo:
        - new A(...)
        - clone a
        - cast<B> a
        - prosto referenciranje: let b = a
        """
        # let name = expr
        _, rest = stmt.split("let", 1)
        name_part, expr_part = rest.split("=", 1)
        var_name = name_part.strip()
        expr = expr_part.strip()

        # let a = new A(1, 2, 3, 4)
        if expr.startswith("new "):
            expr2 = expr[4:].strip()
            cls_name, args_str = expr2.split("(", 1)
            cls_name = cls_name.strip()
            args_str = args_str.rsplit(")", 1)[0]
            args: List[int] = []
            if args_str.strip():
                for tok in args_str.split(","):
                    tok = tok.strip()
                    if not is_int(tok):
                        raise ValueError(
                            "Only int literals allowed as constructor args"
                        )
                    args.append(int(tok))
            inst = self._instantiate(cls_name, args)
            # view tip je na početku ista kao runtime klasa
            self.env[var_name] = VarBinding(inst=inst, view_cls=inst.cls)
            return

        # let c = clone a
        if expr.startswith("clone "):
            src_name = expr[6:].strip()
            src_binding = self._get_binding(src_name)
            new_inst = self._clone(src_binding.inst)
            # clone dobija instancu izvora, view klasa se nasleđuje od view klase izvora
            self.env[var_name] = VarBinding(
                inst=new_inst,
                view_cls=src_binding.view_cls,
            )
            return

        # let c = cast<B> a
        if expr.startswith("cast<"):
            after_cast = expr[len("cast<"):]
            type_part, rest2 = after_cast.split(">", 1)
            target_cls_name = type_part.strip()
            src_name = rest2.strip()
            src_binding = self._get_binding(src_name)
            new_binding = self._cast_binding(src_binding, target_cls_name)
            self.env[var_name] = new_binding
            return

        # let b = a  nova promenljiva koja pokazuje na isti objekat i isti view
        src_name = expr
        src_binding = self._get_binding(src_name)
        self.env[var_name] = VarBinding(
            inst=src_binding.inst,
            view_cls=src_binding.view_cls,
        )

    def _exec_field_assign(self, stmt: str) -> None:
        """
        Obrada 'a.a = 5' - dodela vrednosti polju.
        """
        left, right = stmt.split("=", 1)
        right = right.strip()
        if not is_int(right):
            raise ValueError("Only int literals allowed in field assignment")
        value = int(right)

        obj_part = left.strip()
        var_name, field_name = [p.strip() for p in obj_part.split(".", 1)]
        binding = self._get_binding(var_name)
        inst = binding.inst

        if field_name not in inst.fields:
            raise ValueError(
                f"Unknown field {field_name} "
                f"for instance of {inst.cls.name}"
            )
        inst.fields[field_name] = value

    def _exec_call(self, stmt: str) -> None:
        """
        Obrada 'call a.showAll'.
        Metodu tražimo kroz VIEW klasu, vrednosti čitamo iz inst.fields.
        """
        _, rest = stmt.split("call", 1)
        rest = rest.strip()
        var_part, method_name = [p.strip() for p in rest.split(".", 1)]
        binding = self._get_binding(var_part)
        inst = binding.inst
        view_cls = binding.view_cls

        # pretraga metoda u view tipu (cast<B> znači "posmatraj kao B")
        tokens = view_cls.lookup_method(method_name)
        if tokens is None:
            raise ValueError(
                f"Method {method_name} not found in view type {view_cls.name} "
                f"or its bases"
            )

        values: List[int] = []
        for tok in tokens:
            if is_int(tok):
                # literal se štampa direktno
                values.append(int(tok))
            else:
                # tretiramo tok kao ime polja
                if tok not in inst.fields:
                    raise ValueError(
                        f"Unknown field {tok} "
                        f"in method {method_name}"
                    )
                values.append(inst.fields[tok])

        print(" ".join(str(v) for v in values))

    # ------------- is (instanceof) -------------

    def _exec_is(self, stmt: str) -> None:
        """
        Obrada 'a is A'.
        Koristi stvarnu (runtime) klasu instance, kao instanceof u Javi.
        """
        var_name, cls_name = [p.strip() for p in stmt.split(" is ", 1)]
        binding = self.env.get(var_name)
        cls = self.classes.get(cls_name)
        if binding is None or cls is None:
            print("ISN'T")
            return
        inst = binding.inst
        print("IS" if inst.cls.is_subclass_of(cls) else "ISN'T")

    # ------------- pomoćne funkcije -------------

    def _get_binding(self, name: str) -> VarBinding:
        """
        Pribavlja vezu promenljive iz okruženja.
        """
        if name not in self.env:
            raise ValueError(f"Unknown variable {name}")
        return self.env[name]

    def _instantiate(self, class_name: str, args: List[int]) -> Instance:
        """
        Pravi novu instancu klase sa zadatim argumentima konstruktora.
        Redosled argumenata prati all_fields baze pa izvedene klase.
        """
        if class_name not in self.classes:
            raise ValueError(f"Unknown class {class_name}")
        cls = self.classes[class_name]
        all_fields = cls.all_fields()
        if len(all_fields) != len(args):
            raise ValueError(
                f"Class {class_name} expects {len(all_fields)} args, "
                f"got {len(args)}"
            )
        fields = dict(zip(all_fields, args))
        return Instance(cls=cls, fields=fields)

    def _clone(self, inst: Instance) -> Instance:
        """
        Pravi novu instancu istog runtime tipa sa istim vrednostima polja.
        """
        return Instance(cls=inst.cls, fields=dict(inst.fields))

    def _cast_binding(self, binding: VarBinding, target_cls_name: str) -> VarBinding:
        """
        Upcast kao u Javi:
        - ne pravi novi objekat,
        - menja samo view tip (kroz koji tip gledamo na objekat).

        Sam objekat ostaje isti, pa izmene preko jedne reference
        vide i ostale reference.
        """
        if target_cls_name not in self.classes:
            raise ValueError(f"Unknown class {target_cls_name}")
        target_cls = self.classes[target_cls_name]

        # Dozvoljeno samo ako je runtime klasa podklasa targeta.
        if not binding.inst.cls.is_subclass_of(target_cls):
            raise ValueError(
                f"Cannot cast {binding.inst.cls.name} to {target_cls.name}"
            )

        return VarBinding(inst=binding.inst, view_cls=target_cls)

    def print_classes(self) -> None:
        """
        Ispisuje strukturu svih klasa: bazu, polja i metode.
        """
        print("\n=== Class Structure ===")
        for cls_name in sorted(self.classes.keys()):
            cls = self.classes[cls_name]
            base_name = cls.base.name if cls.base is not None else "None"
            print(f"Class {cls.name}:")
            print(f"  base   : {base_name}")
            print(f"  fields : {', '.join(cls.fields) if cls.fields else '(none)'}")
            if cls.methods:
                print("  methods:")
                for mname, tokens in cls.methods.items():
                    tokens_str = ", ".join(tokens)
                    print(f"    {mname} -> [{tokens_str}]")
            else:
                print("  methods: (none)")
            print()

    def print_instances(self) -> None:
        """
        Ispisuje sve instance iz okruženja:
        - ime promenljive
        - view tip
        - runtime tip
        - polja i vrednosti
        - metode koje se vide kroz view tip.
        """
        print("=== Instances ===")
        if not self.env:
            print("(no instances)")
            return

        for var_name in sorted(self.env.keys()):
            binding = self.env[var_name]
            inst = binding.inst
            view_cls = binding.view_cls

            runtime_cls = inst.cls
            runtime_base = runtime_cls.base.name if runtime_cls.base else "None"
            fields_str = ", ".join(f"{k}={v}" for k, v in inst.fields.items())

            print(f"Instance {var_name}:")
            print(f"  view type    : {view_cls.name}")
            print(f"  runtime type : {runtime_cls.name}")
            print(f"  runtime base : {runtime_base}")
            print(f"  fields       : {fields_str if fields_str else '(none)'}")

            if view_cls.methods:
                mlist = ", ".join(view_cls.methods.keys())
                print(f"  methods (from view type): {mlist}")
            else:
                print("  methods (from view type): (none)")
            print()
