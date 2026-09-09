"""Workbook access: tables, cells, mini Excel-formula evaluator, canonical hash.

The workbook is loaded in FORMULA mode (data_only=False) so persisted PASS
values are never trusted; every metric is recomputed from raw rows.
"""
import datetime as _dt
import hashlib
import json
import re
from functools import lru_cache

import openpyxl
from openpyxl.utils import column_index_from_string, get_column_letter


class Workbook:
    def __init__(self, path):
        self.path = path
        self.wb = openpyxl.load_workbook(path, data_only=False)
        with open(path, "rb") as fh:
            self.file_sha256 = hashlib.sha256(fh.read()).hexdigest()

    # ---------- raw access ----------
    def ws(self, name):
        return self.wb[name]

    def cell(self, sheet, addr):
        return self.wb[sheet][addr].value

    def rows(self, sheet, min_row=1, max_row=None, min_col=1, max_col=None):
        ws = self.wb[sheet]
        return [list(r) for r in ws.iter_rows(min_row=min_row, max_row=max_row or ws.max_row,
                                              min_col=min_col, max_col=max_col or ws.max_column,
                                              values_only=True)]

    def find_header_row(self, sheet, first_cell_text):
        ws = self.wb[sheet]
        for r in range(1, ws.max_row + 1):
            v = ws.cell(r, 1).value
            if isinstance(v, str) and v.strip() == first_cell_text:
                return r
        raise KeyError(f"{sheet}: header row starting with {first_cell_text!r} not found")

    def table(self, sheet, first_cell_text, stop_on_blank_first=True):
        """Return (header_list, list-of-dict rows, first_data_row_number)."""
        ws = self.wb[sheet]
        hr = self.find_header_row(sheet, first_cell_text)
        header = [ws.cell(hr, c).value for c in range(1, ws.max_column + 1)]
        # trim trailing None headers
        while header and header[-1] is None:
            header.pop()
        out = []
        for r in range(hr + 1, ws.max_row + 1):
            vals = [ws.cell(r, c).value for c in range(1, len(header) + 1)]
            if stop_on_blank_first and (vals[0] is None or str(vals[0]).strip() == ""):
                if all(v is None or str(v).strip() == "" for v in vals):
                    break
                # blank first cell but other content: skip (notes rows)
                continue
            d = {}
            for h, v in zip(header, vals):
                if h is None:
                    continue
                d[str(h).strip()] = v
            d["__row"] = r
            out.append(d)
        return header, out, hr + 1

    # ---------- mini formula evaluator ----------
    _RANGE_RE = re.compile(r"^(?:'([^']+)'!|([A-Za-z0-9 _\-]+)!)?\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?$")

    def _parse_ref(self, ref, default_sheet):
        ref = ref.strip()
        m = self._RANGE_RE.match(ref)
        if not m:
            raise ValueError(f"unparseable ref {ref!r}")
        sheet = m.group(1) or m.group(2) or default_sheet
        c1, r1 = column_index_from_string(m.group(3)), int(m.group(4))
        if m.group(5):
            c2, r2 = column_index_from_string(m.group(5)), int(m.group(6))
        else:
            c2, r2 = c1, r1
        return sheet, c1, r1, c2, r2

    def _range_values(self, ref, default_sheet):
        sheet, c1, r1, c2, r2 = self._parse_ref(ref, default_sheet)
        vals = []
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                vals.append(self.eval_cell(sheet, f"{get_column_letter(c)}{r}"))
        return vals

    @staticmethod
    def _split_args(s):
        args, buf, q = [], "", False
        for ch in s:
            if ch == '"':
                q = not q
                buf += ch
            elif ch == "," and not q:
                args.append(buf.strip()); buf = ""
            else:
                buf += ch
        if buf.strip():
            args.append(buf.strip())
        return args

    @staticmethod
    def _crit_match(val, crit):
        if isinstance(crit, str) and crit.startswith('"') and crit.endswith('"'):
            crit = crit[1:-1]
        sval = "" if val is None else str(val)
        if isinstance(crit, str) and crit.startswith("<>"):
            return sval.casefold() != crit[2:].casefold()
        if isinstance(crit, (int, float)):
            try:
                return float(sval) == float(crit)
            except ValueError:
                return False
        return sval.casefold() == str(crit).casefold()

    def _eval_func(self, name, argstr, sheet):
        args = self._split_args(argstr)
        if name == "COUNTA":
            return sum(1 for v in self._range_values(args[0], sheet) if v is not None and str(v) != "")
        if name == "SUM":
            return sum(float(v or 0) for v in self._range_values(args[0], sheet))
        if name == "MAX":
            return max(float(v or 0) for v in self._range_values(args[0], sheet))
        if name == "MIN":
            return min(float(v or 0) for v in self._range_values(args[0], sheet))
        if name == "COUNTIF":
            rng, crit = args
            crit = self._crit_value(crit, sheet)
            return sum(1 for v in self._range_values(rng, sheet) if self._crit_match(v, crit))
        if name == "COUNTIFS":
            pairs = [(args[i], self._crit_value(args[i + 1], sheet)) for i in range(0, len(args), 2)]
            cols = [self._range_values(r, sheet) for r, _ in pairs]
            n = len(cols[0])
            if any(len(c) != n for c in cols):
                raise ValueError("COUNTIFS ranges of unequal size")
            return sum(1 for i in range(n) if all(self._crit_match(cols[k][i], pairs[k][1]) for k in range(len(pairs))))
        raise ValueError(f"unsupported function {name}")

    def _crit_value(self, crit, sheet):
        if crit.startswith('"'):
            return crit
        # cell reference criterion e.g. $A2
        try:
            vals = self._range_values(crit, sheet)
            return vals[0]
        except ValueError:
            return crit

    def eval_formula(self, formula, sheet):
        expr = formula[1:] if formula.startswith("=") else formula
        expr = re.sub(r"^IFERROR\((.+),0\)$", r"(\1)", expr.strip())
        while True:
            m = re.search(r"(COUNTIFS|COUNTIF|COUNTA|SUM|MAX|MIN)\(([^()]*)\)", expr)
            if not m:
                break
            val = self._eval_func(m.group(1), m.group(2), sheet)
            expr = expr[:m.start()] + repr(float(val)) + expr[m.end():]
        expr = re.sub(r"\$?([A-Z]{1,3})\$?(\d+)",
                      lambda mm: repr(float(self.eval_cell(sheet, mm.group(1) + mm.group(2)) or 0)), expr)
        if not re.fullmatch(r"[\d\.\+\-\*/\(\) e]+", expr):
            raise ValueError(f"non-arithmetic residue in {formula!r}: {expr!r}")
        try:
            return eval(expr, {"__builtins__": {}}, {})  # arithmetic only, validated above
        except ZeroDivisionError:
            return 0.0

    @lru_cache(maxsize=None)
    def eval_cell(self, sheet, addr):
        v = self.wb[sheet][addr].value
        if isinstance(v, str) and v.startswith("="):
            return self.eval_formula(v, sheet)
        return v

    # ---------- canonical hash ----------
    def canonical_hash(self, recipe_rows):
        """recipe_rows: list of (label, sheet, range, kind) with kind in {'values','formulas'}."""
        obj = {}
        for label, sheet, rng, kind in recipe_rows:
            _, c1, r1, c2, r2 = self._parse_ref(rng, sheet)
            ws = self.wb[sheet]
            if kind == "values":
                rows = []
                for r in range(r1, r2 + 1):
                    rows.append([_json_safe(ws.cell(r, c).value) for c in range(c1, c2 + 1)])
                obj[label] = rows
            else:
                pairs = []
                for r in range(r1, r2 + 1):
                    for c in range(c1, c2 + 1):
                        v = ws.cell(r, c).value
                        if isinstance(v, str) and v.startswith("="):
                            pairs.append([f"{get_column_letter(c)}{r}", v])
                pairs.sort(key=lambda p: p[0])
                obj[label] = pairs
        payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(payload).hexdigest(), len(payload)


def _json_safe(v):
    if isinstance(v, (_dt.datetime, _dt.date)):
        return v.isoformat()
    return v


# Boolean cells re-saved through openpyxl (workbook v2.19, Cowork) come back in formula mode as the
# literal formulas =TRUE() / =FALSE(); treat them as the booleans they are.
_BOOL_FORMULAS = {"=TRUE()": "TRUE", "=FALSE()": "FALSE"}


def s(v):
    """Cell value to stripped string ('' for None)."""
    if v is None:
        return ""
    if isinstance(v, (_dt.datetime, _dt.date)):
        return v.date().isoformat() if isinstance(v, _dt.datetime) else v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    out = str(v).strip()
    return _BOOL_FORMULAS.get(out.upper().replace(" ", ""), out)


def b(v):
    """Cell value to bool (TRUE/True/1)."""
    if isinstance(v, bool):
        return v
    return s(v).casefold() in ("true", "1", "yes")
