# TODO input args
# output file path: -o (defaults to ./filetree.xml)
# input directory path: -i (defaults to .)
# tab (indent) size: -t (defaults to 2)
# minified: --minified (default false)

# TODO add more to auto-ignore: generate_xml_filetree.py, _xmlft_*
# TODO follow up todo ask llm for good non-text files in repos to ignore

import os
import xml.etree.ElementTree as ET
import fnmatch
import sys

def parse_gitignore(gitignore_path):
    """
    Parse the .gitignore file and return a list of patterns to ignore.
    """
    ignore_patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Ignore empty lines and comments
                if not line or line.startswith('#'):
                    continue
                ignore_patterns.append(line)
    return ignore_patterns

def matches_pattern(path, patterns, repo_root):
    """
    Check if the given path matches any of the ignore patterns.
    """
    matched = False
    # Get the path relative to repo_root, using OS-agnostic separator
    from_path_root = os.path.relpath(path, repo_root)
    for pattern in patterns:
        # Handle negation patterns starting with '!'
        negated = pattern.startswith('!')
        if negated:
            pattern = pattern[1:]

        pattern = pattern.strip()

        # Convert pattern to use OS-agnostic separators
        pattern = pattern.replace('/', os.sep).replace('\\', os.sep)

        # Match path accordingly
        if os.sep in pattern:
            # Pattern has a separator, match from the repo root
            match_path = from_path_root
        else:
            # Match filename only
            match_path = os.path.basename(path)

        if fnmatch.fnmatch(match_path, pattern):
            matched = not negated  # Update matched status
    return matched

def add_directory_to_xml(root_element, current_path, ignore_patterns, repo_root):
    """
    Recursively add directories and files to the XML element,
    excluding those that match the ignore patterns or are hidden.
    """
    entries = []
    try:
        entries = os.listdir(current_path)
    except PermissionError:
        # Skip directories that can't be accessed
        return

    for entry in sorted(entries):
        # Skip hidden files and directories
        if entry.startswith('.'):
            continue

        entry_path = os.path.join(current_path, entry)
        if matches_pattern(entry_path, ignore_patterns, repo_root):
            continue  # Skip ignored files and directories

        if os.path.isdir(entry_path):
            dir_element = ET.SubElement(root_element, 'directory', name=entry)
            add_directory_to_xml(dir_element, entry_path, ignore_patterns, repo_root)
        else:
            ET.SubElement(root_element, 'file', name=entry)

def generate_xml_tree(repo_path, save_output_to_fp=None, minified=False, indent=2):
    """
    Generate an XML tree representation of the repository at repo_path,
    excluding files and directories specified in the .gitignore file.

    Parameters:
    - repo_path: Path to the repository root.
    - save_output_to_fp: File path to save the output XML. Defaults to
                         current working directory + 'filetree.xml'.
    - minified: If True, output will be minified (no indentation).
    - indent: Number of spaces to use for indentation. Default is 2.
              If minified is True, indent is ignored.
    """
    if save_output_to_fp is None:
        save_output_to_fp = os.path.join(os.getcwd(), 'filetree.xml')

    if minified and indent != 2:
        print("Warning: 'indent' is being ignored because 'minified' is True.", file=sys.stderr)

    repo_path = os.path.abspath(repo_path)
    repo_name = os.path.basename(repo_path)
    gitignore_path = os.path.join(repo_path, '.gitignore')
    ignore_patterns = parse_gitignore(gitignore_path)

    root_element = ET.Element('repository', name=repo_name)
    add_directory_to_xml(root_element, repo_path, ignore_patterns, repo_path)

    # Create the ElementTree
    xml_tree = ET.ElementTree(root_element)

    if not minified:
        # Apply indentation for pretty printing
        try:
            # For Python 3.9 and above
            ET.indent(xml_tree, space=' ' * indent, level=0)
        except AttributeError:
            # For older Python versions, define a custom indent function
            def indent_elem(elem, level=0):
                i = "\n" + level * (" " * indent)
                j = "\n" + (level - 1) * (" " * indent)
                if len(elem):
                    if not elem.text or not elem.text.strip():
                        elem.text = i + (" " * indent)
                    for subelem in elem:
                        indent_elem(subelem, level + 1)
                    if not elem.tail or not elem.tail.strip():
                        elem.tail = i
                else:
                    if level and (not elem.tail or not elem.tail.strip()):
                        elem.tail = i
            indent_elem(root_element)
    else:
        # Minified output, remove any whitespace
        pass  # No action needed, default output is minified

    # Write the tree to a file with XML declaration
    xml_tree.write(save_output_to_fp, encoding='utf-8', xml_declaration=False)

    print(f"XML tree has been saved to {save_output_to_fp}")

generate_xml_tree('.')
