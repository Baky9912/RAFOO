# parser.py
# Parser za naš mali jezik: čita CLASS blokove i naredbe.

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from lang_types import ClassDef


class Parser:
    def __init__(self, src: str):
        self.src = src
        self.classes: Dict[str, ClassDef] = {}
        self.statements: List[str] = []

    def parse(self) -> Tuple[Dict[str, ClassDef], List[str]]:
        """
        Glavna ulazna tačka parsiranja.
        Vraća mapu klasa i listu naredbi.
        """
        lines = [l.rstrip() for l in self.src.splitlines()]
        i = 0

        # Prvo parsiramo CLASS blokove.
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("//") or line.startswith(";"):
                i += 1
                continue
            if not line.startswith("CLASS "):
                break
            i = self._parse_class_block(lines, i)

        # Ostatak su naredbe (let, call, is, dodela polja).
        while i < len(lines):
            line = lines[i].strip()
            if line and not line.startswith("//") and not line.startswith(";"):
                self.statements.append(line)
            i += 1

        # Razrešavanje baznih klasa i provera polja.
        self._resolve_bases_and_check_fields()
        return self.classes, self.statements

    def _parse_class_block(self, lines: List[str], i: int) -> int:
        """
        Parsira jedan CLASS blok počevši od linije i.
        Vraća novi indeks i posle bloka.
        """
        header = lines[i].strip()        # npr. "CLASS A"
        _, name = header.split(None, 1)
        name = name.strip()

        base_name: Optional[str] = None
        fields: List[str] = []
        methods: Dict[str, List[str]] = {}

        i += 1
        while i < len(lines):
            line_raw = lines[i]
            line = line_raw.strip()

            # Prazna linija označava kraj bloka klase.
            if not line:
                i += 1
                break
            # Ako naiđemo na novu CLASS, prethodna se završila.
            if line.startswith("CLASS "):
                break

            if line.startswith("base"):
                # base   = B
                part = line.split("=", 1)[1].strip()
                base_name = None if part == "None" else part

            elif line.startswith("fields"):
                # fields = [a, b]
                bracket_part = line.split("=", 1)[1]
                lb = bracket_part.find("[")
                rb = bracket_part.find("]")
                if lb >= 0 and rb >= 0:
                    inner = bracket_part[lb + 1:rb]
                    fields = [f.strip() for f in inner.split(",") if f.strip()]
                else:
                    fields = []

            elif line.startswith("methods"):
                # methods = {
                i += 1
                while i < len(lines):
                    mline = lines[i].strip()
                    if mline.startswith("}"):
                        break
                    if not mline:
                        i += 1
                        continue
                    # showB -> [a, b]
                    if "->" in mline:
                        left, right = mline.split("->", 1)
                        mname = left.strip()
                        rb_part = right.strip()
                        lb = rb_part.find("[")
                        rb = rb_part.find("]")
                        if lb >= 0 and rb >= 0:
                            inner = rb_part[lb + 1:rb]
                            # u metodi tokeni mogu biti imena polja ili int literali
                            tokens = [
                                t.strip()
                                for t in inner.replace(",", " ").split()
                                if t.strip()
                            ]
                        else:
                            tokens = []
                        methods[mname] = tokens
                    i += 1
            i += 1

        cls = ClassDef(name=name, base_name=base_name,
                       fields=fields, methods=methods)
        if name in self.classes:
            raise ValueError(f"Class {name} defined multiple times")
        self.classes[name] = cls
        return i

    def _resolve_bases_and_check_fields(self) -> None:
        """
        Posle parsiranja svih klasa:
        - povezujemo base_name u base referencu
        - proveravamo da izvedena klasa ne redefiniše polja baze.
        """
        # Poveži bazne klase.
        for cls in self.classes.values():
            if cls.base_name is not None:
                if cls.base_name not in self.classes:
                    raise ValueError(
                        f"Unknown base class {cls.base_name} for {cls.name}"
                    )
                cls.base = self.classes[cls.base_name]

        # Zabrani ponovno definisanje polja iz baze.
        for cls in self.classes.values():
            if cls.base is None:
                continue
            inherited = set(cls.base.all_fields())
            for f in cls.fields:
                if f in inherited:
                    raise ValueError(
                        f"Field {f} in class {cls.name} "
                        f"already defined in base class"
                    )
