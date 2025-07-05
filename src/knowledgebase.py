from .formula import Formula, CnfTransformation

class Kb:
    def __init__(self):
        self.formulas = []

    def add(self, formula):
        self.formulas.append(formula)

    def to_cnf(self, method=CnfTransformation.NAIVE):
        if method == CnfTransformation.NAIVE:
            return [f.to_cnf(method=method) for f in self.formulas]
        else:
            raise NotImplementedError("call Tseitin transformation inside the solver per formula!")

    def __str__(self):
        return "\n".join(map(str, self.formulas))

    def __repr__(self):
        return f"Kb(formulas={self.formulas})"

    def get_formulas(self):
        return self.formulas

    def get_atoms_per_formula(self):
        return [sorted(formula.get_atoms()) for formula in self.formulas]