from pysat.formula import WCNF
from itertools import count
from src.formula import FormulaType
from time import time
from pysat.formula import CNF, IDPool
from src.formula import Formula, FormulaType

class MaxSatEncoder:
    
    def __init__(self, kb):
        self.start_time = time()
        self.kb = kb
        self.cnf_formulas = kb.to_cnf()
        self.original_formulas = kb.formulas
        self.original_atoms_per_formula = [f.get_atoms() for f in self.original_formulas]

        self.var_counter = count(start=1)
        self.atom_vars = {} 
        self.formula_vars = []

    def new_var(self):
        return next(self.var_counter)

    def get_var(self, atom, truth_value):
        key = (atom, truth_value)
        if key not in self.atom_vars:
            self.atom_vars[key] = self.new_var()
        return self.atom_vars[key]

    def encode(self):
        wcnf = WCNF()

        all_atoms = set().union(*self.original_atoms_per_formula)
        for atom in all_atoms:
            a_true = self.get_var(atom, 't')
            a_false = self.get_var(atom, 'f')
            a_both = self.get_var(atom, 'b')

            # A_true ∨ A_false ∨ A_both (at least one)
            wcnf.append([a_true, a_false, a_both])

            # ¬A_true ∨ ¬A_false
            wcnf.append([-a_true, -a_false])

            # ¬A_true ∨ ¬A_both
            wcnf.append([-a_true, -a_both])

            # ¬A_false ∨ ¬A_both
            wcnf.append([-a_false, -a_both])

        # Formula dependent clauses
        for idx, cnf_formula in enumerate(self.cnf_formulas):
            finc = self.new_var()
            self.formula_vars.append(finc)

            original_atoms = self.original_atoms_per_formula[idx]

            # F_inconsistent_i ∨ ¬A_both for each Atom in the original formula
            for atom in original_atoms:
                a_both = self.get_var(atom, 'b')
                wcnf.append([finc, -a_both])

            # CNF-Clauses as Hard Clauses + A_both
            clauses = self.extract_clauses(cnf_formula)
            for clause in clauses:
                atoms_in_clause = self.get_atoms_from_clause(clause)
                extended_clause = clause + [self.get_var(atom, 'b') for atom in atoms_in_clause]
                wcnf.append(extended_clause)

            # Soft Clause: ¬F_inconsistent_i / weight: 1
            wcnf.append([-finc], weight=1)

        #print(wcnf.hard)

        end_time = time()
        elapsed_time = end_time - self.start_time

        return wcnf, elapsed_time

    # Extracts all clauses from a CNF-formula
    def extract_clauses(self, formula):

        def recurse(f):
            if f.type == FormulaType.AND:
                return recurse(f.left) + recurse(f.right)
            elif f.type == FormulaType.OR:
                return [self.extract_clause_literals(f)]
            else:
                return [self.extract_clause_literals(f)]

        return recurse(formula)

    # Extracts the literals from a clause
    def extract_clause_literals(self, formula):

        if formula.type == FormulaType.OR:
            return self.extract_clause_literals(formula.left) + self.extract_clause_literals(formula.right)
        elif formula.type == FormulaType.ATOM:
            return [self.get_var(formula.atom, 't')]
        elif formula.type == FormulaType.NOT and formula.left.type == FormulaType.ATOM:
            return [self.get_var(formula.left.atom, 'f')]
        else:
            raise ValueError(f"Unknown clause structure: {formula}")
        
    # Extracts the atoms from a clause    
    def get_atoms_from_clause(self, clause):
        atoms = set()
        for lit in clause:
            for (atom, truth_val), var in self.atom_vars.items():
                if abs(lit) == var and truth_val in ('t', 'f'):
                    atoms.add(atom)
                    break
        return atoms
