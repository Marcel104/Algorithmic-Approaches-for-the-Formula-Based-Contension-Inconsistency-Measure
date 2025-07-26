from time import perf_counter
from .formula import Formula, FormulaType

TRUTH_VALUE_T = "t"
TRUTH_VALUE_F = "f"
TRUTH_VALUE_B = "b"
FORMULA_IS_ATOM = "formula_is_atom"
NEGATION = "negation"
CONJUNCTION = "conjunction"
DISJUNCTION = "disjunction"
CONJUNCT_OF = "conjunct_of"
DISJUNCT_OF = "disjunct_of"
NUM_CONJUNCTS = "num_conjuncts"
NUM_DISJUNCTS = "num_disjuncts"
TRUTH_VALUE_PREDICATE = "val"
ATOM = "atom"
KB_MEMBER = "kb"
FORMULA_PREFIX = "f"
F_INCONSISTENT = "f_inconsistent"

class ASPEncoder:
    def __init__(self):
        self.start_time = perf_counter()

    def add_truth_values(self):
        return f"tv({TRUTH_VALUE_T}).\ntv({TRUTH_VALUE_B}).\ntv({TRUTH_VALUE_F}).\n"

    def add_atom_rules(self, kb):
        atoms = set()
        for formula in kb.get_formulas():
            atoms.update(formula.get_atoms())
        return ''.join(f"{ATOM}({a.lower()}).\n" for a in atoms)

    def pl_to_asp(self, formula, formula_name, rules):
        if formula.is_atom():
            atom_name = formula.get_name().lower()
            rules.append(f"{FORMULA_IS_ATOM}({formula_name},{atom_name}).\n")
            return

        if formula.is_negation():
            sub = next(iter(formula.get_subformulas()))
            new_formula_name = formula_name + "_n"
            rules.append(f"{NEGATION}({new_formula_name},{formula_name}).\n")
            self.pl_to_asp(sub, new_formula_name, rules)
            return

        if formula.is_conjunction():
            conjuncts = formula.get_subformulas()
            rules.append(f"{CONJUNCTION}({formula_name}).\n")
            rules.append(f"{NUM_CONJUNCTS}({formula_name},{len(conjuncts)}).\n")
            for i, conjunct in enumerate(conjuncts):
                sub_name = f"{formula_name}_{i}"
                rules.append(f"{CONJUNCT_OF}({sub_name},{formula_name}).\n")
                self.pl_to_asp(conjunct, sub_name, rules)
            return

        if formula.is_disjunction():
            disjuncts = formula.get_subformulas()
            rules.append(f"{DISJUNCTION}({formula_name}).\n")
            rules.append(f"{NUM_DISJUNCTS}({formula_name},{len(disjuncts)}).\n")
            for i, disjunct in enumerate(disjuncts):
                sub_name = f"{formula_name}_{i}"
                rules.append(f"{DISJUNCT_OF}({sub_name},{formula_name}).\n")
                self.pl_to_asp(disjunct, sub_name, rules)
            return

        if formula.is_implication():
            left, right = formula.get_subformulas()
            disj = Formula(FormulaType.OR, Formula(FormulaType.NOT, left), right)
            self.pl_to_asp(disj, formula_name, rules)
            return

        if formula.is_equivalence():
            left, right = formula.get_subformulas()
            disj1 = Formula(FormulaType.OR, Formula(FormulaType.NOT, left), right)
            disj2 = Formula(FormulaType.OR, Formula(FormulaType.NOT, right), left)
            conj = Formula(FormulaType.AND, disj1, disj2)
            self.pl_to_asp(conj, formula_name, rules)
            return

        if formula.is_tautology():
            rules.append(f"{TRUTH_VALUE_PREDICATE}({formula_name},{TRUTH_VALUE_T}).\n")
            return

        if formula.is_contradiction():
            rules.append(f"{TRUTH_VALUE_PREDICATE}({formula_name},{TRUTH_VALUE_F}).\n")
            return

    def handle_formulas_in_kb(self, kb):
        formula_rules = []
        for i, formula in enumerate(kb.get_formulas()):
            formula_name = f"{FORMULA_PREFIX}{i}"
            formula_rules.append(f"{KB_MEMBER}({formula_name}).\n")
            self.pl_to_asp(formula, formula_name, formula_rules)
        return ''.join(formula_rules)

    def add_conjunction_rules(self):
        return (
            f"{TRUTH_VALUE_PREDICATE}(Y,{TRUTH_VALUE_T}):{CONJUNCTION}(Y):-N{{"
            f"{TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_T}):{CONJUNCT_OF}(X,Y)}}N,"
            f"{NUM_CONJUNCTS}(Y,N).\n"
            f"{TRUTH_VALUE_PREDICATE}(Y,{TRUTH_VALUE_F}):{CONJUNCTION}(Y):-1{{"
            f"{TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_F})}},{CONJUNCT_OF}(X,Y).\n"
            f"{TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_B}):-{CONJUNCTION}(X),"
            f"not {TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_T}),"
            f"not {TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_F}).\n"
        )

    def add_disjunction_rules(self):
        return (
            f"{TRUTH_VALUE_PREDICATE}(Y,{TRUTH_VALUE_T}):{DISJUNCTION}(Y):-1{{"
            f"{TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_T})}},{DISJUNCT_OF}(X,Y).\n"
            f"{TRUTH_VALUE_PREDICATE}(Y,{TRUTH_VALUE_F}):{DISJUNCTION}(Y):-N{{"
            f"{TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_F}):{DISJUNCT_OF}(X,Y)}}N,"
            f"{NUM_DISJUNCTS}(Y,N).\n"
            f"{TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_B}):-{DISJUNCTION}(X),"
            f"not {TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_T}),"
            f"not {TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_F}).\n"
        )

    def add_negation_rules(self):
        return (
            f"{TRUTH_VALUE_PREDICATE}(Y,{TRUTH_VALUE_T}):-{NEGATION}(X,Y),"
            f"{TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_F}).\n"
            f"{TRUTH_VALUE_PREDICATE}(Y,{TRUTH_VALUE_F}):-{NEGATION}(X,Y),"
            f"{TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_T}).\n"
            f"{TRUTH_VALUE_PREDICATE}(Y,{TRUTH_VALUE_B}):-{NEGATION}(X,Y),"
            f"{TRUTH_VALUE_PREDICATE}(X,{TRUTH_VALUE_B}).\n"
        )
    
    def add_formula_atom_links(self, kb):
        rules = []
        for i, formula in enumerate(kb.get_formulas()):
            formula_name = f"{FORMULA_PREFIX}{i}"
            atoms = formula.get_atoms()
            for atom in atoms:
                rules.append(f"formula_contains_atom({formula_name},{atom.lower()}).\n")
        return ''.join(rules)

    def encode(self, kb):
        if len(kb.get_formulas()) == 0:
            return 0

        program = ""

        # Truth-Values facts
        program += self.add_truth_values() # noch in Arbeit erklären

        # formula cant be false
        program += f":- {TRUTH_VALUE_PREDICATE}(X, {TRUTH_VALUE_F}), {KB_MEMBER}(X).\n"

        # exactly one truth value for each atom
        program += f"1{{{TRUTH_VALUE_PREDICATE}(X,Y) : tv(Y)}}1 :- {ATOM}(X).\n"

        # atom facts, with formula_is_atom
        program += self.add_atom_rules(kb)

        # rules for formulas in the knowledge base
        program += self.handle_formulas_in_kb(kb)

        # Connectivity rules for formulas
        program += f"{TRUTH_VALUE_PREDICATE}(X,Z):tv(Z):- {FORMULA_IS_ATOM} (X,Y), {TRUTH_VALUE_PREDICATE} (Y,Z).\n" # noch in Arbeit erklären
        if CONJUNCTION in program:
            program += self.add_conjunction_rules()
        if DISJUNCTION in program:
            program += self.add_disjunction_rules()
        if NEGATION in program:
            program += self.add_negation_rules()

        # rules to combine formulas and their atoms
        program += self.add_formula_atom_links(kb)

        # A Formula is inconsistent if it contains at least one atom with the value 'b'
        program += f"{F_INCONSISTENT}(F) :- {KB_MEMBER}(F), formula_contains_atom(F,A), {TRUTH_VALUE_PREDICATE}(A,{TRUTH_VALUE_B}).\n" # formula_contains_atom noch in Arbeit erklären

        # at least inconsistwent formulas as possible
        program += f"#minimize {{ 1,F : {F_INCONSISTENT}(F) }}.\n"

        program += f"#show val(X,Y) : atom(X), val(X,Y).\n"
        program += f"#show f_inconsistent/1.\n"

        #print(program)

        end_time = perf_counter()
        elapsed_time = end_time - self.start_time

        return program, elapsed_time
