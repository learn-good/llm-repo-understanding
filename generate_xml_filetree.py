# Creates an XML filetree for a repo
import os
import xml.etree.ElementTree as ET
import fnmatch
from utils import log

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
    Handles negations properly by processing patterns in order.
    """
    from_path_root = os.path.relpath(path, repo_root)
    ignored = False
    
    for pattern in patterns:
        # Handle negation patterns
        is_negation = pattern.startswith('!')
        if is_negation:
            pattern = pattern[1:]
        
        # Clean up pattern
        pattern = pattern.strip()
        pattern = pattern.replace('/', os.sep).replace('\\', os.sep)
        
        # For patterns starting with /, match from repo root
        if pattern.startswith(os.sep):
            pattern = pattern[1:]  # Remove leading slash
            match_path = from_path_root
        else:
            # For patterns without leading /, match against basename or relative path
            if os.sep in pattern:
                match_path = from_path_root
            else:
                match_path = os.path.basename(path)
        
        # Check if path matches pattern
        matches = fnmatch.fnmatch(match_path, pattern)
        
        if matches:
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


def add_directory_to_xml(root_element, current_path, ignore_patterns, repo_root):
    """
    Recursively add directories and files to the XML element,
    excluding those that match the ignore patterns or are hidden.
    """
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
        if matches_pattern(entry_path, ignore_patterns, repo_root):
            continue

        # Recursively add entry to tree
        if os.path.isdir(entry_path):
            dir_element = ET.SubElement(root_element, 'directory', name=entry)
            add_directory_to_xml(dir_element, entry_path, ignore_patterns, repo_root)
        else:
            attributes = {'name': entry}
            if not is_text_file(entry_path): # flag non-readable files as not-text
                attributes['text-readable'] = 'false'
            ET.SubElement(root_element, 'file', attributes)


def generate_xml_tree(input_filepath=".", use_gitignore=True,
                      output_filepath=None, output_minified=False, 
                      output_indent=2, output_overwrite=False):
    """
    Generate an XML tree representation of the repository at repo_path,
    excluding files and directories specified in the .gitignore file.

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
    if output_filepath is None: # use default output dir
        outputs_dir = os.path.join('outputs', repo_name)
        os.makedirs(outputs_dir, exist_ok=True)
        output_filepath = os.path.join(outputs_dir, 'filetree.xml')
    else: # use given output dir
        output_dir = os.path.dirname(output_filepath)
        if output_dir:  # Only create if there's actually a directory path
            os.makedirs(output_dir, exist_ok=True)

    # Ignore patterns using .gitignore
    if use_gitignore:
        gitignore_path = os.path.join(input_filepath, '.gitignore')
        ignore_patterns = parse_gitignore(gitignore_path)
    else:
        ignore_patterns = []

    # Create the ElementTree from the repo
    root_element = ET.Element('repository', name=repo_name)
    add_directory_to_xml(root_element, input_filepath, ignore_patterns, input_filepath)
    xml_tree = ET.ElementTree(root_element)

    # Indent filetree
    if not output_minified:
        # Apply indentation for pretty printing
        try:
            # For Python 3.9 and above
            ET.indent(xml_tree, space=' ' * output_indent, level=0)
        except AttributeError:
            # For older Python versions, define a custom indent function
            def indent_elem(elem, level=0):
                i = "\n" + level * (" " * output_indent)
                j = "\n" + (level - 1) * (" " * output_indent)
                if len(elem):
                    if not elem.text or not elem.text.strip():
                        elem.text = i + (" " * output_indent)
                    for subelem in elem:
                        indent_elem(subelem, level + 1)
                    if not elem.tail or not elem.tail.strip():
                        elem.tail = i
                else:
                    if level and (not elem.tail or not elem.tail.strip()):
                        elem.tail = i
            indent_elem(root_element)
    # Minified output, remove any whitespace
    else:
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