from pysat.formula import WCNF
from pysat.formula import CNF, IDPool
from src.formula import Formula, FormulaType, CnfTransformation
from time import perf_counter


class MaxSatEncoder:

    def __init__(self, kb):
        self.start_time = perf_counter()
        self.kb = kb
        self.cnf_formulas = kb.to_cnf()
        self.original_formulas = kb.formulas
        self.original_atoms_per_formula = [f.get_atoms() for f in self.original_formulas]

        self.pool = IDPool()
        self.atom_vars = {} 
        self.formula_vars = []

    def new_var(self):
        return self.pool.id()

    def get_var(self, atom, truth_value):
        key = (atom, truth_value)
        if key not in self.atom_vars:
            self.atom_vars[key] = self.pool.id()
        return self.atom_vars[key]

    def get_atoms_from_clause_ids(self, clause):
        atoms = set()
        for lit in clause:
            var = abs(lit)
            for (atom, tv), v in self.atom_vars.items():
                if v == var:
                    atoms.add(atom)
                    break
        return atoms

    def encode(self):
        wcnf = WCNF()

        # A_true/A_false/A_both constraints for original atoms
        all_atoms = set().union(*self.original_atoms_per_formula)
        for atom in all_atoms:
            a_true = self.get_var(atom, 't')
            a_false = self.get_var(atom, 'f')
            a_both = self.get_var(atom, 'b')

            wcnf.append([a_true, a_false, a_both])
            wcnf.append([-a_true, -a_false])
            wcnf.append([-a_true, -a_both])
            wcnf.append([-a_false, -a_both])

        atom_true_varmap = {atom: self.get_var(atom, 't') for atom in all_atoms}

        for idx, formula in enumerate(self.original_formulas):
            finc = self.new_var()
            self.formula_vars.append(finc)

            original_atoms = self.original_atoms_per_formula[idx]

            # F_inconsistent_i ∨ ¬A_both for each original atom
            for atom in original_atoms:
                a_both = self.get_var(atom, 'b')
                wcnf.append([finc, -a_both])

            # create tseitin clauses with a global variable pool
            top_var, tseitin_clauses = formula.to_cnf(
                method=CnfTransformation.TSEITIN,
                id_pool=self.pool,
                atom_true_varmap=atom_true_varmap
            )

            if not tseitin_clauses:
                # atomic formulas without tseitin clauses
                atoms_in_clause = self.get_atoms_from_clause_ids([top_var])
                extended_clause = [top_var] + [self.get_var(atom, 'b') for atom in atoms_in_clause if atom in original_atoms]
                wcnf.append(extended_clause)
            else:
                wcnf.append([top_var])
                for clause in tseitin_clauses:
                    mapped_clause = []
                    for lit in clause:
                        var = abs(lit)
                        sign = 1 if lit > 0 else -1
                        for (atom, truth_val), v in self.atom_vars.items():
                            if v == var:
                                if truth_val != 't':
                                    continue

                                if sign == 1:
                                    mapped_clause.append(self.get_var(atom, 't'))
                                else:
                                    mapped_clause.append(self.get_var(atom, 'f'))
                                break
                        else:
                            mapped_clause.append(lit)

                    atoms_in_clause = self.get_atoms_from_clause_ids(mapped_clause)
                    extended_clause = mapped_clause + [self.get_var(atom, 'b') for atom in atoms_in_clause if atom in original_atoms]
                    wcnf.append(extended_clause)

            wcnf.append([-finc], weight=1)

        #print(wcnf.hard)

        end_time = perf_counter()
        elapsed_time = end_time - self.start_time

        return wcnf, elapsed_time

    def extract_clauses(self, formula):
        def recurse(f):
            if f.type == FormulaType.AND:
                return recurse(f.left) + recurse(f.right)
            elif f.type == FormulaType.OR:
                return [self.extract_clause_literals(f)]
            else:
                return [self.extract_clause_literals(f)]
        return recurse(formula)

    def extract_clause_literals(self, formula):
        if formula.type == FormulaType.OR:
            return self.extract_clause_literals(formula.left) + self.extract_clause_literals(formula.right)
        elif formula.type == FormulaType.ATOM:
            return [self.get_var(formula.atom, 't')]
        elif formula.type == FormulaType.NOT and formula.left.type == FormulaType.ATOM:
            return [self.get_var(formula.left.atom, 'f')]
        else:
            raise ValueError(f"Unknown clause structure: {formula}")

    def get_atoms_from_clause(self, clause):
        atoms = set()
        for lit in clause:
            for (atom, truth_val), var in self.atom_vars.items():
                if abs(lit) == var and truth_val in ('t', 'f'):
                    atoms.add(atom)
                    break
        return atoms
