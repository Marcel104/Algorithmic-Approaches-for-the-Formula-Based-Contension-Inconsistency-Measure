import time
import multiprocessing
import csv
import os
from src.solver_Max_SAT import solve_maxsat, generate_dynamic_clauses, get_both_atoms
from src.parser import parse_kb_to_cnf, structure_knowledgebase
from src.solver_ASP import solve_asp

directory_path = "data"
log_file = "log.csv"
TIMEOUT = 5

def initialize_csv():
    if not os.path.exists(log_file):
        with open(log_file, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["filepath", "filename", "solver", "state", "runtime (ms)", "parse-time (ms)", "Ifc", "atoms_valued_both"])

def get_all_files(directory):
    return {os.path.join(root, f): f for root, _, files in os.walk(directory) for f in files}

def write_result(row):
    with open(log_file, mode="a", newline="") as file:
        csv.writer(file).writerow(row)

def handle_process(process, result_queue, filepath, filename, solver):
    process.start()
    process.join(TIMEOUT)
    if process.is_alive():
        print(f"{filename}: Timeout after {TIMEOUT}s in {solver}.")
        process.terminate()
        process.join()
        write_result([filepath, filename, solver, "timeout", "N/A", "N/A", "N/A", "N/A"])
    else:
        result = result_queue.get() if not result_queue.empty() else None
        if result:
            write_result(result)
            print(f"{filepath}: {filename} {solver} (time: {result[4]} ms, parse: {result[5]} ms), Ifc: {result[6]}, atoms_valued_both: {result[7]}")

def process_file_Max_SAT(filename, filepath, cnf, parse_time, result_queue):
    try:
        start = time.perf_counter()

        hard, soft, mapping = generate_dynamic_clauses(cnf)
        model, weight = solve_maxsat(cnf, "Minisat22", hard, soft)
        atoms_both = get_both_atoms(model, mapping)

        end = time.perf_counter()

        result_queue.put((filepath, filename, "Max-SAT",
                          "solution found" if model else "no solution",
                          f"{(end - start) * 1000:.2f}",
                          parse_time,
                          weight, atoms_both))
    except Exception as e:
        result_queue.put((filepath, filename, "Max-SAT", f"Error: {str(e)}", "N/A", "N/A", "N/A", "N/A"))

def process_file_ASP(filename, filepath, cnf, parse_time, result_queue):
    try:
        start = time.perf_counter()

        solution_found, atoms_both, ifc = solve_asp(cnf)

        end = time.perf_counter()

        result_queue.put((filepath, filename, "ASP", 
                          "solution found" if solution_found else "no solution",
                          f"{(end - start) * 1000:.2f}", 
                          parse_time, 
                          ifc, atoms_both))
    except Exception as e:
        result_queue.put((filepath, filename, "ASP", f"Error: {str(e)}", "N/A", "N/A", "N/A", "N/A"))

if __name__ == '__main__':
    multiprocessing.freeze_support()
    initialize_csv()
    files = get_all_files(directory_path)

    for filepath, filename in files.items():

        start_parse = time.perf_counter()
        structured_knowledgebase = structure_knowledgebase(filepath)
        cnf = parse_kb_to_cnf(structured_knowledgebase)
        end_parse = time.perf_counter()

        for solver, func in [("Max-SAT", process_file_Max_SAT), ("ASP", process_file_ASP)]:
            result_queue = multiprocessing.Queue()
            proc = multiprocessing.Process(target=func, args=(filename, filepath, cnf, f"{(end_parse - start_parse) * 1000:.2f}", result_queue))
            handle_process(proc, result_queue, filepath, filename, solver)
