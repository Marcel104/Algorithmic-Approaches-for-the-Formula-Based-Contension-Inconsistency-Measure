class Kb:
    def __init__(self):
        self.formulas = []

    def add(self, formula):
        self.formulas.append(formula)

    def to_cnf(self):
        return [f.to_cnf() for f in self.formulas]

    def __str__(self):
        return "\n".join(map(str, self.formulas))

    def __repr__(self):
        return f"Kb(formulas={self.formulas})"

    def get_formulas(self):
        return self.formulas

    def get_atoms_per_formula(self):
        return [sorted(formula.get_atoms()) for formula in self.formulas]