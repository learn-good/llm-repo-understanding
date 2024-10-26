import tiktoken
import os
import argparse
import xml.etree.ElementTree as ET
import statistics
from utils import log

def is_ignored(element):
    """
    Check if an XML element should be ignored based on the 'ignore="true"' attribute.
    """
    return element.get('ignore', '').lower() == 'true'

def is_not_text_readable(element):
    return element.get('text-readable', '').lower() == 'false'

def count_tokens(text, encoding):
    """
    Count the number of tokens in the given text using tiktoken encoding.
    """
    tokens = encoding.encode(text, allowed_special={'<|endoftext|>'})
    return len(tokens)

def traverse_xml(element, current_path, stats, thresholds, encoding):
    """
    Recursively traverse the XML tree, updating stats accordingly.
    """
    if is_ignored(element) or is_not_text_readable(element):
        return

    if element.tag == 'file':
        stats['total_files'] += 1

        filename = element.get('name')
        file_path = os.path.join(current_path, filename)

        # Infer file type from extension
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1

        if os.path.exists(file_path):
            try:
                if element.get('text-readable', 'true').lower() == 'true':
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        content_token_count = count_tokens(content, encoding)
                        stats['file_content_token_count'] += content_token_count
                        # Store tuple of (token_count, file_path)
                        stats['file_content_token_counts'].append((content_token_count, file_path))
                    except Exception as e:
                        print(f"Error reading file '{file_path}': {e}")
                else:
                    # Non-text-readable file
                    pass
            except Exception as e:
                log.error(f"Error accessing file '{file_path}': {e}")

    elif element.tag == 'directory' or element.tag == 'repository':
        # Handle directories and the root 'repository' element
        if element.tag == 'directory':
            stats['total_directories'] += 1

        dirname = element.get('name') if element.tag == 'directory' else ''
        dir_path = os.path.join(current_path, dirname) if dirname else current_path

        # Count direct files and subdirectories
        num_direct_files = len([child for child in element if child.tag == 'file' and not is_ignored(child)])
        num_direct_dirs = len([child for child in element if child.tag in ['directory'] and not is_ignored(child)])

        # Warn if directory has many items
        total_direct_items = num_direct_files + num_direct_dirs
        if total_direct_items > thresholds['dir_items_threshold']:
            log.warning(f"Directory '{dir_path}' has {total_direct_items} items (files/directories).")

        # Recursively traverse children
        for child in element:
            traverse_xml(child, dir_path, stats, thresholds, encoding)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Get information about the XML filetree.')
    parser.add_argument('-f', '--filetree-path', required=True,
                        help='Path to the XML filetree file.')
    parser.add_argument('-d', '--directory', required=True,
                        help='Base directory path of the repository.')
    parser.add_argument('--dir-items-threshold', type=int, default=100,
                        help='Threshold for number of direct items in a directory to issue a warning.')
    parser.add_argument('--large-file-thresholds', nargs='*', type=int,
                        default=[50_000, 100_000],
                        help='Thresholds (in tokens) for large file warnings.')
    parser.add_argument('--encoding-name', default='o200k_base',
                        help='The tiktoken encoding name to use for tokenization (default: o200k_base).')
    args = parser.parse_args()
    return args

def main():
    args = parse_arguments()

    if not os.path.exists(args.filetree_path):
        log.error(f"XML file '{args.filetree_path}' does not exist.")
        return

    if not os.path.isdir(args.directory):
        log.error(f"Base directory '{args.directory}' does not exist or is not a directory.")
        return

    # Initialize tiktoken encoding
    try:
        encoding = tiktoken.get_encoding(args.encoding_name)
    except Exception as e:
        log.error(f"Error initializing tiktoken encoding '{args.encoding_name}': {e}")
        return

    # Parse the XML filetree
    tree = ET.parse(args.filetree_path)
    root = tree.getroot()

    stats = {
        'total_files': 0,
        'total_directories': 0,
        'file_content_token_count': 0,
        'file_types': {},
        'file_content_token_counts': [],  # List of token counts per file
    }

    thresholds = {
        'dir_items_threshold': args.dir_items_threshold,
        'large_file_thresholds': sorted(args.large_file_thresholds),
    }

    # Start traversal from the root element
    traverse_xml(root, args.directory, stats, thresholds, encoding)

    # Print statistics
    print("\n=== Statistics ===")
    print(f"Total files: {stats['total_files']}")
    print(f"Total directories: {stats['total_directories']}")
    print(f"Total file content tokens: {stats['file_content_token_count']}")

    # Token statistics and large files
    if stats['file_content_token_counts']:
        # Sort files by token count (descending)
        sorted_files = sorted(stats['file_content_token_counts'], reverse=True)
        
        # Calculate statistics
        token_counts = [count for count, _ in sorted_files]
        mean_tokens = statistics.mean(token_counts)
        median_tokens = statistics.median(token_counts)
        max_tokens = token_counts[0]
        
        print(f"\nToken Statistics:")
        print(f"Mean tokens per file: {mean_tokens:.2f}")
        print(f"Median tokens per file: {median_tokens}")
        print(f"Max tokens: {max_tokens}")
        
        # Print large files section
        print("\n=== Largeset Files (by token count) ===")
        # You can adjust this number to show more or fewer files
        top_n = 5
        for token_count, file_path in sorted_files[:top_n]:
            print(f"{token_count:,} tokens: {file_path}")
    else:
        print("\nNo token counts to report for file contents.")

    # File type distribution
    print("\nFile type distribution:")
    for file_type, count in sorted(stats['file_types'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {file_type if file_type else '[no extension]'}: {count} files")
    print(f"\nNote: The actual run will use likely a multiple of the input tokens (e.g. 10 * {stats['file_content_token_count']}) of the base files, since we are generating summaries of those files that will themselves become inputs into other summarization steps. We do not attempt to estimate the number of output tokens.")

if __name__ == '__main__':
    main()