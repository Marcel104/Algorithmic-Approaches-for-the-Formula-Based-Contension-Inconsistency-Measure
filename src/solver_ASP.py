from clingo import Control

def generate_asp_code(knowledgebase):
    atome = set()
    rules = []
    formula_counter = 0

    # Atome extrahieren und Negation prüfen
    for formel in knowledgebase:
        for klausel in formel:
            for literal in klausel:
                atom = abs(literal)
                atome.add(atom)

    # ASP-Code für Atomdeklarationen
    asp_code = "% Deklaration der Atome\n"
    for atom in sorted(list(atome)):
        asp_code += f"atom({atom}).\n"
    asp_code += "\n"

    # ASP-Code für mögliche Wahrheitswerte
    asp_code += "% Mögliche Wahrheitswerte für jedes Atom: true (t), false (f), both (b)\n"
    asp_code += "{ val(A, t) } :- atom(A), not val(A, f), not val(A, b).\n"
    asp_code += "{ val(A, f) } :- atom(A), not val(A, t), not val(A, b).\n"
    asp_code += "{ val(A, b) } :- atom(A), not val(A, t), not val(A, f).\n\n"

    # ASP-Code für die Wissensbasis (Formeln und Klauseln)
    asp_code += "% Definition der Wissensbasis (Formeln und Klauseln)\n"
    for formel_klauseln in knowledgebase:
        formula_id = f"f{formula_counter}"
        rules.append(f"formula({formula_id}).")
        for i, klausel in enumerate(formel_klauseln):
            klausel_id = f"k{i}"
            rules.append(f"klausel({formula_id}, {klausel_id}).")
            for literal in klausel:
                atom = abs(literal)
                if literal < 0:
                    neg_id = f"neg_{atom}"
                    rules.append(f"neg_atom({atom}, {neg_id}).")
                    rules.append(f"in_klausel({formula_id}, {klausel_id}, {neg_id}).")
                else:
                    rules.append(f"in_klausel({formula_id}, {klausel_id}, {atom}).")
        formula_counter += 1
    asp_code += "\n".join(rules) + "\n\n"

    # ASP-Code für die Erfüllung von Klauseln
    asp_code += "% Eine Klausel ist erfüllt, wenn mindestens ein Literal in ihr wahr ist\n"
    asp_code += "klausel_erfuellt(F, K) :- klausel(F, K), in_klausel(F, K, L), literal_satisfied(L).\n\n"

    # ASP-Code für die Erfüllung von Formeln
    asp_code += "% Eine Formel ist erfüllt, wenn alle ihre Klauseln erfüllt sind\n"
    asp_code += "erfuellt(F, K) :- formula(F), klausel(F, K), klausel_erfuellt(F, K).\n"
    asp_code += "formel_erfuellt(F) :- formula(F), not not erfuellt(F, K) : klausel(F, K).\n\n"

    # ASP-Code für die Erfüllung eines Literals
    asp_code += "% Ein Literal ist erfüllt:\n"
    asp_code += "literal_satisfied(A) :- val(A, t).\n"
    asp_code += "literal_satisfied(A) :- val(A, b).\n"
    asp_code += "literal_satisfied(N) :- neg_atom(B, N), val(B, f).\n"
    asp_code += "literal_satisfied(N) :- neg_atom(B, N), val(B, b).\n\n"

    # Bedingung, dass alle Formeln erfüllt sein müssen
    asp_code += "% Alle Formeln müssen erfüllt sein\n"
    asp_code += ":- formula(F), not formel_erfuellt(F).\n\n"

    # ASP-Code zur Identifizierung der inkonsistenten Formeln
    asp_code += "% Eine Formel ist inkonsistent, wenn sie ein Atom mit dem Wert both enthält\n"
    asp_code += "f_inconsistent(F) :- formula(F), in_klausel(F, K, A), val(A, b), not neg_atom(_, A).\n"
    asp_code += "f_inconsistent(F) :- formula(F), in_klausel(F, K, N), neg_atom(A, N), val(A, b).\n\n"
    asp_code += "#minimize { 1 : f_inconsistent(F) }.\n\n"

    # Ausgabeanweisungen
    asp_code += "both(A) :- val(A, b).\n\n"
    asp_code += "#show val/2.\n"
    asp_code += "#show formel_erfuellt/1.\n"
    asp_code += "#show f_inconsistent/1.\n"
    asp_code += "#show both/1.\n"


    return asp_code

# Führt den ASP Code in Clingo aus
def run_clingo(asp_code):
    try:
        ctl = Control(["0"])
        ctl.configuration.solve.opt_mode = "opt"
        ctl.add("base", [], asp_code)
        ctl.ground([("base", [])])

        answer_sets = []
        with ctl.solve(yield_=True) as handle:
            for model in handle:
                answer_sets.append(model.symbols(shown=True))
        return answer_sets
    except Exception as e:
        print(f"Error (Clingo):\n{e}")
        return None

def solve_asp(knowledgebase):
    asp_code = generate_asp_code(knowledgebase)

    # ASP Code in Datei schreiben
    #with open("generated_ASP_Code.lp", "w") as f:
        #f.write(asp_code)

    answer_sets = run_clingo(asp_code)

    both_atoms = []
    inconsistent_count = 0

    if answer_sets:
        solution_found = True
        first_set = answer_sets[0]
        for symbol in first_set:
            if symbol.name == "both" and len(symbol.arguments) == 1:
                both_atoms.append(symbol.arguments[0].number)
            elif symbol.name == "f_inconsistent":
                inconsistent_count += 1
    else:
        solution_found = False
        print("\nNo Answer Sets found.")

    return solution_found, both_atoms, inconsistent_count
