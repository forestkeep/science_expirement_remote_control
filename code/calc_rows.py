import os

def count_lines_in_file(file_path):
    """Count lines in the file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return sum(1 for line in file if line.strip())

def count_lines_in_directory(directory):
    """Count lines in all Python files in the directory and subdirectories."""
    total_lines = 0
    file_lines = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                lines = count_lines_in_file(file_path)
                file_lines.append((file_path, lines))
                total_lines += lines

    return file_lines, total_lines

def print_report(file_lines, total_lines):
    """Output results in table format."""
    sorted_file_lines = sorted(file_lines, key=lambda x: x[1])

    print(f"{'File':<55} {'Line Count':<20}")
    print("=" * 70)
    for file_path, lines in sorted_file_lines:
        if lines > 1000:
            color = '\033[91m'  # Red
        elif lines > 500:
            color = '\033[93m'  # Yellow
        else:
            color = '\033[0m'   # Normal color
        print(f"{color}{file_path:<55} {lines:<20}\033[0m")

    print("=" * 70)
    print(f"{'Total line count:':<60} {total_lines}")

directory_path = '.'
file_lines, total_lines = count_lines_in_directory(directory_path)
print_report(file_lines, total_lines)
