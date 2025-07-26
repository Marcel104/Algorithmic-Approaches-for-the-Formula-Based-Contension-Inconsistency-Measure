from src.parser import Parser
from pysat.examples.rc2 import RC2
import clingo
import csv
import os
from time import perf_counter
from multiprocessing import Process, Queue
import sys

sys.setrecursionlimit(2000)
directory_path = "data\SRS"
log_file_general = "log.csv"
log_file_maxsat = "log_MaxSAT.csv"
TIMEOUT = 1000

def wrapper(q, func, args):
    try:
        result = func(*args)
        q.put(("success", result))
    except Exception as e:
        q.put(("error", e))

def run_with_timeout(func, args=(), timeout=10):
    q = Queue()
    p = Process(target=wrapper, args=(q, func, args))
    p.start()
    p.join(timeout)

    if p.is_alive():
        p.terminate()
        p.join()
        return "timeout", None

    if q.empty():
        return "error", Exception("Function did not return anything")

    status, result = q.get()
    if status == "error":
        raise result
    return "success", result

def initialize_csv(filepath, headers):
    if not os.path.exists(filepath):
        with open(filepath, mode="w", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(headers)

def get_all_files(directory):
    return {
        os.path.join(root, f): f
        for root, _, files in os.walk(directory)
        for f in files
    }

def write_result(filepath, row):
    with open(filepath, mode="a", newline="") as file:
        csv.writer(file, delimiter=";").writerow(row)

def format_time(value):
    return f"{round(value * 1000, 2):.2f}".replace(".", ",")

def asp_encode_and_solve(kb_content):
    parser = Parser()
    kb = parser.parse_kb_from_string(kb_content)

    from src.solver_ASP import ASPEncoder
    start_time = perf_counter()
    asp_encoder = ASPEncoder()
    program, encode_time = asp_encoder.encode(kb)

    ctl = clingo.Control(["--opt-mode=optN"])
    ctl.add("base", [], program)
    ctl.ground([("base", [])])

    optimal_cost = None
    atom_values = []
    f_inconsistent = []

    def on_model(model):
        nonlocal optimal_cost, atom_values, f_inconsistent
        costs = model.cost
        if costs:
            current_cost = costs[0]
            if optimal_cost is None or current_cost < optimal_cost:
                optimal_cost = current_cost
                atom_values = []
                f_inconsistent = []
                for atom in model.symbols(shown=True):
                    if atom.name == "f_inconsistent" and len(atom.arguments) == 1:
                        f_inconsistent.append(f"{str(atom.arguments[0]).upper()}")
                    if atom.name == "val" and len(atom.arguments) == 2:
                        atom_values.append(f"{str(atom.arguments[0])}:{atom.arguments[1]}")
        elif optimal_cost is None:
            optimal_cost = 0

    ctl.configuration.solve.opt_mode = "opt"
    ctl.solve(on_model=on_model)

    total_time = perf_counter() - start_time
    f_inconsistent.sort()
    atom_values.sort(key=lambda x: x.split(":")[0])
    return optimal_cost, f_inconsistent, atom_values, total_time, encode_time

def maxsat_encode_and_solve(kb_content):
    parser = Parser()
    kb = parser.parse_kb_from_string(kb_content)

    from src.solver_max_SAT_naive import MaxSatEncoder
    start_time = perf_counter()
    msat_encoder = MaxSatEncoder(kb)
    wcnf, encode_time = msat_encoder.encode()

    reverse_varmap = {v: k for k, v in msat_encoder.atom_vars.items()}

    atom_values = []
    f_inconsistent = []
    
    with RC2(wcnf) as rc2:
        model = rc2.compute()
        cost = rc2.cost
        model_set = set(model)

        for v in model:
            if v > 0 and v in reverse_varmap:
                atom, kind = reverse_varmap[v]
                atom_values.append(f"{atom}:{kind}")

        for i, (clause, weight) in enumerate(zip(wcnf.soft, wcnf.wght)):
            satisfied = any(
                (lit in model_set if lit > 0 else -lit not in model_set) for lit in clause
            )
            if not satisfied:
                f_inconsistent.append(f"F{i}")

    total_time = perf_counter() - start_time
    f_inconsistent.sort()
    atom_values.sort(key=lambda x: x.split(":")[0])

    return cost, model, f_inconsistent, atom_values, total_time, encode_time, len(wcnf.hard)

def maxsat_tseitin_encode_and_solve(kb_content):
    parser = Parser()
    kb = parser.parse_kb_from_string(kb_content)

    from src.solver_max_SAT_Tseitin import MaxSatEncoder
    start_time = perf_counter()
    msat_encoder = MaxSatEncoder(kb)
    wcnf, encode_time = msat_encoder.encode()

    reverse_varmap = {v: k for k, v in msat_encoder.atom_vars.items()}

    atom_values = []
    f_inconsistent = []
    
    with RC2(wcnf) as rc2:
        model = rc2.compute()
        cost = rc2.cost
        model_set = set(model)

        for v in model:
            if v > 0 and v in reverse_varmap:
                atom, kind = reverse_varmap[v]
                atom_values.append(f"{atom}:{kind}")

        for i, (clause, weight) in enumerate(zip(wcnf.soft, wcnf.wght)):
            satisfied = any(
                (lit in model_set if lit > 0 else -lit not in model_set) for lit in clause
            )
            if not satisfied:
                f_inconsistent.append(f"F{i}")

    total_time = perf_counter() - start_time
    f_inconsistent.sort()
    atom_values.sort(key=lambda x: x.split(":")[0])

    return cost, model, f_inconsistent, atom_values, total_time, encode_time, len(wcnf.hard)

if __name__ == "__main__":
    headers_general = ["filepath", "filename", "solver", "solve-time (ms)", "parse-time (ms)", "runtime (ms)", "IFC", "inconsistent_formulas", "atoms_valued_both"]
    headers_maxsat = headers_general + ["number_hard_clauses"]

    initialize_csv(log_file_general, headers_general)
    initialize_csv(log_file_maxsat, headers_maxsat)

    files = get_all_files(directory_path)

    for filepath, filename in files.items():
        print(f"Processing file: {filename}")
        with open(filepath, 'r') as file:
            kb_content = file.read()

        #####################
        ##### ASP Start #####
        #####################
        try:
            status, result = run_with_timeout(asp_encode_and_solve, args=(kb_content,), timeout=TIMEOUT)
            if status == "timeout":
                print("ASP Timeout")
                asp_cost = asp_f_inconsistent = asp_atom_values = asp_total_time = asp_time_encoder = None
            else:
                asp_cost, asp_f_inconsistent, asp_atom_values, asp_total_time, asp_time_encoder = result
                print(f"ASP IFC: {asp_cost}, InconsistentFormulas: {asp_f_inconsistent}, Atoms: {asp_atom_values}")

            row = [
                filepath, filename, "ASP",
                format_time(asp_total_time - asp_time_encoder) if asp_time_encoder is not None and asp_total_time is not None else "Timeout",
                format_time(asp_time_encoder) if asp_time_encoder is not None else "",
                format_time(asp_total_time) if asp_total_time is not None else "",
                asp_cost, asp_f_inconsistent, asp_atom_values
            ]

            write_result(log_file_general, row)

        except MemoryError:
            print(f"ASP MemoryError for file: {filename}")
            row = [filepath, filename, "ASP", "", "", "", "MemoryError", "", ""]
            write_result(log_file_general, row)
        except Exception as e:
            print(f"ASP Error for file: {filename}: {e}")
            row = [filepath, filename, "ASP", "", "", "", f"Error: {e}", "", ""]
            write_result(log_file_general, row)


        ######################
        ## MaxSAT (N) Start ##
        ######################
        try:
            status, result = run_with_timeout(maxsat_encode_and_solve, args=(kb_content,), timeout=TIMEOUT)
            if status == "timeout":
                print("MaxSAT (Naiv) Timeout")
                msat_cost = msat_f_inconsistent = msat_atom_values = msat_total_time = msat_time_encoder = wcnf_hard_clauses = None
            else:
                msat_cost, msat_model, msat_f_inconsistent, msat_atom_values, msat_total_time, msat_time_encoder, wcnf_hard_clauses = result
                print(f"MSAT (Naiv) IFC: {msat_cost}, InconsistentFormulas: {msat_f_inconsistent}, Atoms: {msat_atom_values}")

            row_general = [
                filepath, filename, "MaxSAT (Naiv)",
                format_time(msat_total_time - msat_time_encoder) if msat_time_encoder is not None and msat_total_time is not None else "Timeout",
                format_time(msat_time_encoder) if msat_time_encoder is not None else "",
                format_time(msat_total_time) if msat_total_time is not None else "",
                msat_cost, msat_f_inconsistent, msat_atom_values
            ]
            row_maxsat = row_general + [wcnf_hard_clauses]

            write_result(log_file_general, row_general)
            write_result(log_file_maxsat, row_maxsat)

        except MemoryError:
            print(f"MaxSAT (Naiv) MemoryError for file: {filename}")
            row_general = [filepath, filename, "MaxSAT (Naiv)", "", "", "", "MemoryError", "", ""]
            row_maxsat = row_general + [""]
            write_result(log_file_general, row_general)
            write_result(log_file_maxsat, row_maxsat)
        except Exception as e:
            print(f"MaxSAT (Naiv) Error for file: {filename}: {e}")
            row_general = [filepath, filename, "MaxSAT (Naiv)", "", "", "", f"Error: {e}", "", ""]
            row_maxsat = row_general + [""]
            write_result(log_file_general, row_general)
            write_result(log_file_maxsat, row_maxsat)

        ######################
        ## MaxSAT (T) Start ##
        ######################
        try:
            status, result = run_with_timeout(maxsat_tseitin_encode_and_solve, args=(kb_content,), timeout=TIMEOUT)
            if status == "timeout":
                print("MaxSAT (Tseitin) Timeout")
                msat_cost = msat_f_inconsistent = msat_atom_values = msat_total_time = msat_time_encoder = wcnf_hard_clauses = None
            else:
                msat_cost, msat_model, msat_f_inconsistent, msat_atom_values, msat_total_time, msat_time_encoder, wcnf_hard_clauses = result
                print(f"MSAT (Tseitin) IFC: {msat_cost}, InconsistentFormulas: {msat_f_inconsistent}, Atoms: {msat_atom_values}")

            row = [
                filepath, filename, "MaxSAT (Tseitin)",
                format_time(msat_total_time - msat_time_encoder) if msat_time_encoder is not None and msat_total_time is not None else "Timeout",
                format_time(msat_time_encoder) if msat_time_encoder is not None else "",
                format_time(msat_total_time) if msat_total_time is not None else "",
                msat_cost, msat_f_inconsistent, msat_atom_values, wcnf_hard_clauses
            ]

            write_result(log_file_maxsat, row)

        except MemoryError:
            print(f"MaxSAT (Tseitin) MemoryError for file: {filename}")
            row = [filepath, filename, "MaxSAT (Tseitin)", "", "", "", "MemoryError", "", "", ""]
            write_result(log_file_maxsat, row)
        except Exception as e:
            print(f"MaxSAT (Tseitin) Error for file: {filename}: {e}")
            row = [filepath, filename, "MaxSAT (Tseitin)", "", "", "", f"Error: {e}", "", "", ""]
            write_result(log_file_maxsat, row)