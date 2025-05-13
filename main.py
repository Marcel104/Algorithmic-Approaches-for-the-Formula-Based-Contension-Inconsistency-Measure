from src.parser import Parser
from src.solver_Max_SAT import MaxSatEncoder
from src.solver_ASP import ASPEncoder
from pysat.examples.rc2 import RC2
import clingo
import csv
import os
from time import time
import threading

directory_path = "data"
log_file = "log.csv"
TIMEOUT = 5

def timeout_func():
    raise TimeoutError("Function call timed out")

def initialize_csv():
    if not os.path.exists(log_file):
        with open(log_file, mode="w", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["filepath", "filename", "solver", "solve-time (ms)", "parse-time (ms)", "runtime (ms)", "IFC","inconsistent_formulas", "atoms_valued_both"])

def get_all_files(directory):
    return {os.path.join(root, f): f for root, _, files in os.walk(directory) for f in files}

def write_result(row):
    with open(log_file, mode="a", newline="") as file:
        csv.writer(file, delimiter=";").writerow(row)

def format_time(value):
    return f"{round(value * 1000, 2):.2f}".replace(".", ",")

def process_file_ASP(program: str) -> int:
    timer = threading.Timer(TIMEOUT, timeout_func)

    try:
        timer.start()
        start_time = time()
        ctl = clingo.Control(["--opt-mode=optN"])
        ctl.add("base", [], program)
        ctl.ground([("base", [])])

        optimal_cost = None
        atom_values = []
        f_inconsistent = []

        # if model is found
        def on_model(model):
            nonlocal optimal_cost, atom_values, f_inconsistent
            costs = model.cost
            if costs:
                current_cost = costs[0]
                # if model is better, continue and clear current lists
                if optimal_cost is None or current_cost < optimal_cost:
                    optimal_cost = current_cost

                    atom_values = []
                    f_inconsistent = []

                    # collect all atoms and inconsistent formulas in the model
                    for atom in model.symbols(atoms=True, shown = True):
                        if atom.name == "f_inconsistent" and len(atom.arguments) == 1:
                            f_inconsistent.append(f"{str(atom.arguments[0]).upper()}")
                        if atom.name == "val" and len(atom.arguments) == 2 and str(atom.arguments[0]).startswith("a"):
                            atom_values.append(f"{str(atom.arguments[0]).upper()}:{atom.arguments[1]}")
            elif optimal_cost is None:
                optimal_cost = 0

        ctl.configuration.solve.opt_mode = "opt"
        ctl.solve(on_model=on_model)

        end_time = time()
        elapsed_time = end_time - start_time

        f_inconsistent.sort(key=lambda x: int(x[1:]))
        atom_values.sort(key=lambda x: int(x[1:].split(":")[0]))

        timer.cancel()
        return optimal_cost, f_inconsistent, atom_values, elapsed_time

    except TimeoutError:
        print("ASP Timeout")
        return None, None, None, None

def process_file_Max_SAT(wcnf, reverse_varmap):
    atom_values = []
    f_inconsistent = []

    timer = threading.Timer(TIMEOUT, timeout_func)

    with RC2(wcnf) as rc2:
        try:
            timer.start()
            start_time = time()
            model = rc2.compute()
            end_time = time()
            elapsed_time = end_time - start_time
            model_set = set(model)
            cost = rc2.cost

            # Collect all atoms in the model
            for v in model:
                if v > 0 and v in reverse_varmap:
                    atom, kind = reverse_varmap[v]
                    atom_values.append(f"{atom}:{kind}")

            # Collect all inconsistent formulas in the model (here unsatisified soft-clauses)
            for i, (clause, weight) in enumerate(zip(wcnf.soft, wcnf.wght)):
                satisfied = False

                for lit in clause:
                    is_satisfied = (
                        lit in model_set if lit > 0 else (-lit not in model_set)
                    )
                    if is_satisfied:
                        satisfied = True

                if not satisfied:
                    f_inconsistent.append(f"F{i}")

            f_inconsistent.sort(key=lambda x: int(x[1:]))
            atom_values.sort(key=lambda x: int(x[1:].split(":")[0]))

            timer.cancel()
            return cost, model, f_inconsistent, atom_values, elapsed_time
        except TimeoutError:
            print("MaxSAT Timeout")
            return None, None, None, None, None


if __name__ == "__main__":

    initialize_csv()

    files = get_all_files(directory_path)

    for filepath, filename in files.items():
        print(f"Processing file: {filename}")

        with open(filepath, 'r') as file:
            kb_content = file.read()

        parser = Parser()
        kb = parser.parse_kb_from_string(kb_content)

        ####################
        ##### ASP Start ####
        ####################
        asp_encoder = ASPEncoder()
        program, asp_time_encoder = asp_encoder.encode(kb)

        asp_cost, asp_f_inconsistent, asp_atom_values, asp_solve_time = process_file_ASP(program)
        print(f"ASP IFC: {asp_cost}, InconsistentFormulas: {asp_f_inconsistent}, Atoms: {asp_atom_values}")

        ####################
        ### MaxSAT Start ###
        ####################
        msat_encoder = MaxSatEncoder(kb)
        wcnf, msat_time_encoder = msat_encoder.encode()

        reverse_varmap = {v: k for k, v in msat_encoder.atom_vars.items()}
        msat_cost, msat_model, msat_f_inconsistent, msat_atom_values, msat_solve_time = process_file_Max_SAT(wcnf, reverse_varmap)
        print(f"MSAT IFC: {msat_cost}, InconsistentFormulas: {msat_f_inconsistent}, Atoms: {msat_atom_values}")

        ####################
        ## Results to CSV ##
        ####################
        row = [filepath, filename, "ASP", format_time(asp_solve_time), format_time(asp_time_encoder), format_time(asp_solve_time + asp_time_encoder), asp_cost, asp_f_inconsistent, asp_atom_values]
        write_result(row)

        row = [filepath, filename, "MaxSAT", format_time(msat_solve_time), format_time(msat_time_encoder), format_time(msat_solve_time + msat_time_encoder), msat_cost, msat_f_inconsistent, msat_atom_values]
        write_result(row)

        if asp_cost != msat_cost:
            print(f"ASP and MaxSAT results are different: {filename}.")