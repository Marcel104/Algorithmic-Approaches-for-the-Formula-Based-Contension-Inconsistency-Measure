from pysat.formula import WCNF
from pysat.examples.rc2 import RC2

def generate_dynamic_clauses(knowledgebase):
    hard_clauses = []
    soft_clauses = []
    atoms = set()
    formula_atoms = {}

    for i, formula in enumerate(knowledgebase):  
        atoms_in_formula = set()
        for literal in formula:
            atom = abs(literal)
            atoms.add(atom)
            atoms_in_formula.add(atom)
        formula_atoms[i] = atoms_in_formula

    # Variablen für A_true, A_false und A_both erstellen
    num_atoms = len(atoms)
    atom_mapping = {atom: (i + 1, i + num_atoms + 1, i + 2 * num_atoms + 1) for i, atom in enumerate(atoms)}

    # Hard Clauses für dreiwertige Logik erstellen
    for atom, (a_true, a_false, a_both) in atom_mapping.items():
        hard_clauses.append([a_true, a_false, a_both])  # A true ∨ A false ∨ A both
        hard_clauses.append([-a_true, -a_false])  # ¬A true ∨ ¬A false
        hard_clauses.append([-a_true, -a_both])  # ¬A true ∨ ¬A both
        hard_clauses.append([-a_false, -a_both])  # ¬A false ∨ ¬A both

    # Zusätzliche Variablen für F_inconsistent für jede Formel
    num_formulas = len(knowledgebase)
    f_inconsistent_vars = {i: 3 * num_atoms + 1 + i for i in range(num_formulas)}

    # Hard Clauses für jede Formel und jedes Atom darin
    for formula_idx, atom_set in formula_atoms.items():
        f_inconsistent_i = f_inconsistent_vars[formula_idx]
        for atom in atom_set:
            a_both = atom_mapping[atom][2]
            hard_clauses.append([f_inconsistent_i, -a_both])  # F_inconsistent_i ∨ ¬A_both

    # Hard Clauses für jede Klausel innerhalb der CNF-Form
    for clause in knowledgebase:
        clause_literals = []
        for literal in clause:
            atom = abs(literal)
            if literal > 0:
                clause_literals.append(atom_mapping[atom][0])  # A_true wenn positiv
            else:
                clause_literals.append(atom_mapping[atom][1])  # A_false wenn negativ
            clause_literals.append(atom_mapping[atom][2])  # A_both immer hinzufügen
        hard_clauses.append(clause_literals)  # Disjunktion aller Li und Lb

    # Soft Clauses für jede Formel hinzufügen
    for formula_idx in range(num_formulas):
        soft_clauses.append(([-f_inconsistent_vars[formula_idx]], 1))  # ¬F_inconsistent_i (Gewicht 1)

    return hard_clauses, soft_clauses

def solve_maxsat(knowledgebase, solver_name="Glucose3", hard_clauses=None, soft_clauses=None):

    solver_map = {
        "Glucose3": "g3",
        "Lingeling": "lgl",
        "Cadical153": "cd15",
        "Cadical195": "cd19",
        "Gluecard41": "gc4",
        "Minisat22": "m22"
    }
    
    if solver_name not in solver_map:
        raise ValueError(f"invalid solver name: {solver_name}")
    
    wcnf = WCNF()

    # Hard Clauses hinzufügen
    if hard_clauses:
        for clause in hard_clauses:
            wcnf.append(clause)

    # Soft Clauses hinzufügen
    if soft_clauses:
        for clause, weight in soft_clauses:
            wcnf.append(clause, weight=weight)

    # Falls keine separaten Hard- oder Soft Clauses übergeben wurden, nutze die Knowledgebase als Hard Clauses
    if hard_clauses is None and soft_clauses is None:
        wcnf.hard.extend(knowledgebase)

    rc2 = None
    try:
        rc2 = RC2(wcnf, solver=solver_map[solver_name])
        rc2.compute()
        opt_cost = rc2.cost
        model = rc2.model if rc2.model is not None else []

        return model, opt_cost

    except Exception as e:
        print(f"Error: {e}")
        return None

    finally:
        if rc2:
            rc2.delete()