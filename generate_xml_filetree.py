import os
import xml.etree.ElementTree as ET
import fnmatch
from utils import log, indent_xml_filetree

def parse_gitignore(gitignore_path):
    """
    Parse the .gitignore file and return a list of patterns to ignore.
    Each pattern is a tuple (pattern, base_path)
    """
    ignore_patterns = []
    base_path = os.path.dirname(gitignore_path)

    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                ignore_patterns.append((line, base_path))
    return ignore_patterns

def matches_pattern(path, ignore_patterns):
    """
    Determines whether a path matches any of the ignore patterns.
    """
    ignored = False

    for pattern, base_path in ignore_patterns:
        is_negation = pattern.startswith('!')
        if is_negation:
            pattern = pattern[1:]

        pattern = pattern.strip()

        if not pattern:
            continue  # Skip empty patterns
        if pattern.startswith('#'):
            continue  # Skip comments

        # Adjust for escaping spaces
        pattern = pattern.replace('\\ ', ' ')  # Unescape spaces

        # Convert path to match to relative path from base_path
        rel_path = os.path.relpath(path, base_path)
        rel_path = rel_path.replace(os.sep, '/')  # Normalize path separators

        # Handle patterns starting with '/'
        if pattern.startswith('/'):
            pattern = pattern.lstrip('/')
        else:
            # For patterns without leading '/', they can match any subpath
            pass

        # Handle patterns ending with '/'
        match_directory_only = False
        if pattern.endswith('/'):
            match_directory_only = True
            pattern = pattern.rstrip('/')
            if not os.path.isdir(path):
                continue  # Skip if pattern is for directory but path is not a directory

        # Perform the match
        # Using fnmatchcase to match case-sensitive (consistent with gitignore behavior in Unix)
        if fnmatch.fnmatchcase(rel_path, pattern):
            if match_directory_only and not os.path.isdir(path):
                continue  # Skip if pattern is directory-only but path is not a directory
            ignored = not is_negation

    return ignored

def is_text_file(file_path, sample_size=8192):
    """
    Check if a file is readable as text by examining its contents.

    Args:
        file_path (str): Path to the file to check
        sample_size (int): Number of bytes to check (default: 8192)

    Returns:
        bool: True if the file appears to be text, False otherwise
    """
    try:
        # Check if file is empty
        if os.path.getsize(file_path) == 0:
            return True

        # Try to read the first chunk of the file
        with open(file_path, 'rb') as f:
            chunk = f.read(sample_size)

        # Check for NULL bytes - a strong indicator of binary content
        if b'\x00' in chunk:
            return False

        # Try to decode as UTF-8
        try:
            chunk.decode('utf-8')
            return True
        # Try to decode as latin-1
        except UnicodeDecodeError:
            try:
                chunk.decode('latin-1')
                return True
            except UnicodeDecodeError:
                return False

    # If we can't read the file, assume it's not text
    except (IOError, OSError):
        return False

def add_directory_to_xml(root_element, current_path, ignore_patterns):
    """
    Recursively add directories and files to the XML element,
    excluding those that match the ignore patterns or are hidden.
    """
    # Check for .gitignore in current directory
    gitignore_path = os.path.join(current_path, '.gitignore')
    if os.path.exists(gitignore_path):
        current_ignore_patterns = parse_gitignore(gitignore_path)
        # Combine ignore patterns from parent directories with current directory
        ignore_patterns = ignore_patterns + current_ignore_patterns

    entries = []
    try:
        entries = os.listdir(current_path)
    except PermissionError as e:
        # Skip directories that can't be accessed
        log.error(f"Permission error: {e}")
        return

    for entry in sorted(entries):
        # Skip hidden files and directories
        if entry.startswith('.'):
            continue

        entry_path = os.path.join(current_path, entry)

        # Skip ignored files and directories
        if matches_pattern(entry_path, ignore_patterns):
            continue

        # Recursively add entry to tree
        if os.path.isdir(entry_path):
            dir_element = ET.SubElement(root_element, 'directory', name=entry)
            add_directory_to_xml(dir_element, entry_path, ignore_patterns)
        else:
            attributes = {'name': entry}
            if not is_text_file(entry_path):  # Flag non-readable files as not-text
                attributes['text-readable'] = 'false'
            ET.SubElement(root_element, 'file', attributes)

def generate_xml_tree(input_filepath=".", use_gitignore=True,
                      output_filepath=None, output_minified=False,
                      output_indent=2, output_overwrite=False):
    """
    Generate an XML tree representation of the repository at repo_path,
    excluding files and directories specified in .gitignore files.

    Parameters:
    - input_filepath:  Path to the repository root.
    - output_filepath: File path to save the output XML. If None, defaults to
                       'outputs/{repo_name}/filetree.xml'.
    - output_minified: If True, output will be minified (no indentation).
    - output_indent:   Number of spaces to use for indentation. Default is 2.
                       If minified is True, indent is ignored.
    """
    # Get the repository name from the path, if repo_name is empty (in case of '.'), use 'root'
    input_filepath = os.path.abspath(input_filepath)
    repo_name = os.path.basename(input_filepath)

    # Create outputs directory if it doesn't exist
    if output_filepath is None:  # Use default output dir
        outputs_dir = os.path.join('outputs', repo_name)
        os.makedirs(outputs_dir, exist_ok=True)
        output_filepath = os.path.join(outputs_dir, 'filetree.xml')
    else:  # Use given output dir
        output_dir = os.path.dirname(output_filepath)
        if output_dir:  # Only create if there's actually a directory path
            os.makedirs(output_dir, exist_ok=True)

    # Initialize ignore patterns
    ignore_patterns = []

    # Create the ElementTree from the repo
    root_element = ET.Element('repository', name=repo_name)
    add_directory_to_xml(root_element, input_filepath, ignore_patterns)
    xml_tree = ET.ElementTree(root_element)

    # Indent filetree
    if not output_minified:
        indent_xml_filetree(xml_tree, root_element, output_indent)
    else:  # Minified output, remove any whitespace
        pass  # No action needed, default output is minified

    # Check if user meant to overwrite
    if os.path.exists(output_filepath):
        if not output_overwrite:
            while True:
                response = input(f"Output file '{output_filepath}' already exists. Overwrite? (y/n): ").lower()
                if response in ['yes', 'y']:
                    break
                elif response in ['no', 'n']:
                    print("Operation cancelled.")
                    return
                else:
                    print("Please answer 'yes/y' to overwrite or 'no/n' to cancel.")

    # Write the tree to a file with XML declaration
    xml_tree.write(output_filepath, encoding='utf-8', xml_declaration=False)
    print(f"XML tree has been saved to {output_filepath}")

def parse_arguments():
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate XML tree representation of a directory structure.')

    parser.add_argument('-i', '--input',
                      help='Input directory path to generate XML tree from.',
                      default=".")

    parser.add_argument('-o', '--output',
                      help='Output file path (defaults to ./outputs/{repo_name}/filetree.xml)')

    parser.add_argument('-t', '--tab-size',
                      type=int,
                      default=2,
                      help='Tab (indent) size (defaults to 2)')

    parser.add_argument('--minified',
                      action='store_true',
                      help='Output minified XML (default: False)')

    parser.add_argument('--no-ignore',
                      action='store_true',
                      help='Do not respect .gitignore patterns for creating the filetree')

    parser.add_argument('--overwrite',
                      action='store_true',
                      help='Overwrite output file if it exists')

    args = parser.parse_args()

    # Validate tab size
    if args.tab_size <= 0:
        parser.error("Tab size must be greater than 0")

    return args

def main():
    """Main function to handle argument parsing and XML tree generation."""
    args = parse_arguments()

    # Generate XML tree with provided arguments
    generate_xml_tree(
        input_filepath   = args.input,
        use_gitignore    = not args.no_ignore,
        output_filepath  = args.output,
        output_minified  = args.minified,
        output_indent    = args.tab_size,
        output_overwrite = args.overwrite
    )

if __name__ == "__main__":
    main()