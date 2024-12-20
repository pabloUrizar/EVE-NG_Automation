import os
import json
import argparse

def load_json(file_path):
    """Load a JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file {file_path}: {e}")
        return None

def resolve_name(path, solution_objects, student_objects):
    """
    Replace numeric ids in the path with their names from solution and student objects
    """
    segments = path.split('.')
    for i, segment in enumerate(segments):
        if segment in solution_objects:
            segments[i] = solution_objects[segment]
        elif segment in student_objects:
            segments[i] = student_objects[segment]
    return '.'.join(segments)

def compare_dictionaries(solution, student, path="", solution_objects=None, student_objects=None):
    """
    Compare two dictionaries and return a list of differences
    """
    differences = []

    for key in solution:
        solution_value = solution[key]
        student_value = student.get(key, None)
        current_path = f"{path}.{key}" if path else key

        if isinstance(solution_value, dict) and isinstance(student_value, dict):
            differences.extend(compare_dictionaries(solution_value, student_value, current_path, solution_objects, student_objects))
        elif isinstance(solution_value, list) and isinstance(student_value, list):
            if sorted(solution_value) != sorted(student_value):
                resolved_path = resolve_name(current_path, solution_objects, student_objects)
                differences.append({
                    "path": resolved_path,
                    "solution": solution_value,
                    "student": student_value
                })
        else:
            # Exclude cases where solution == None and student does not have the key
            if solution_value is None and student_value is None:
                continue
            if student_value is None:
                resolved_path = resolve_name(current_path, solution_objects, student_objects)
                differences.append({
                    "path": resolved_path,
                    "solution": solution_value,
                    "student": "Missing in student"
                })
            elif solution_value != student_value:
                resolved_path = resolve_name(current_path, solution_objects, student_objects)
                differences.append({
                    "path": resolved_path,
                    "solution": solution_value,
                    "student": student_value
                })

    for key in student:
        if key not in solution:
            current_path = f"{path}.{key}" if path else key
            resolved_path = resolve_name(current_path, solution_objects, student_objects)
            differences.append({
                "path": resolved_path,
                "solution": "Missing in solution",
                "student": student[key]
            })

    return differences

def compare_json_files(parsed_json, solution_json, solution_objects, student_objects):
    """
    Compare the parsed JSON files with the specified solution.
    Return a list of the differences found
    """
    return compare_dictionaries(solution_json, parsed_json, solution_objects=solution_objects, student_objects=student_objects)

def generate_report(parsed_dir, solution_file, output_dir):
    """Generate comparison reports for every parsed file"""
    solution_json = load_json(solution_file)
    if solution_json is None:
        print(f"Failed to load the solution file: {solution_file}")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Extract object names from the solution
    solution_objects = {router_id: router["name"] for router_id, router in solution_json["nodes"].items()}

    parsed_files = [f for f in os.listdir(parsed_dir) if f.endswith('.json') and f != os.path.basename(solution_file)]

    for parsed_file in parsed_files:
        parsed_path = os.path.join(parsed_dir, parsed_file)
        parsed_json = load_json(parsed_path)
        if parsed_json is None:
            print(f"Error loading {parsed_path}")
            continue

        # Extract object names from the student's file
        student_objects = {router_id: router["name"] for router_id, router in parsed_json.get("nodes", {}).items()}

        differences = compare_json_files(parsed_json, solution_json, solution_objects, student_objects)

        # Generate the text report
        report_file_txt = os.path.join(output_dir, f"report_{os.path.splitext(parsed_file)[0]}.txt")
        with open(report_file_txt, 'w') as f:
            if differences:
                f.write("Differences found:\n\n")
                for diff in differences:
                    f.write(f"Difference in {diff['path']}:\n")
                    f.write(f"  Solution: {diff['solution']}\n")
                    f.write(f"  Student: {diff['student']}\n\n")
            else:
                f.write("No differences found.\n")

        # Generate the JSON report
        report_file_json = os.path.join(output_dir, f"report_{os.path.splitext(parsed_file)[0]}.json")
        with open(report_file_json, 'w') as f:
            json.dump({"differences": differences}, f, indent=4)

        print(f"Reports generated: {report_file_txt}, {report_file_json}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate comparison reports between parsed JSON files and a solution.")
    parser.add_argument("--parsed-dir", required=True, help="Directory containing the parsed JSON files.")
    parser.add_argument("--output-dir", required=True, help="Directory to save the generated reports.")
    parser.add_argument("--solution-file", required=True, help="JSON file containing the solution.")

    args = parser.parse_args()

    generate_report(args.parsed_dir, args.solution_file, args.output_dir)
