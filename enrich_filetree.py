import os
import xml.etree.ElementTree as ET
import argparse
import asyncio
import tiktoken
from utils import (
    request_chat_completion, 
    extract_xml, 
    read_file_to_text, 
    replace_placeholders,
    log
)

DEFAULT_SEMAPHORE_SIZE = 10

def create_mirrored_repo_structure(source_dir: str, mirror_base: str) -> None:
    for root, _, _ in os.walk(source_dir):
        # Calculate relative path from source_dir
        rel_path = os.path.relpath(root, source_dir)
        mirror_path = os.path.join(mirror_base, rel_path)
        
        # Create the directory in mirror location
        os.makedirs(mirror_path, exist_ok=True)


def get_mirror_path(original_path: str, root_dir: str, mirror_base: str) -> str:
    """Get the corresponding path in the mirror structure"""
    rel_path = os.path.relpath(original_path, root_dir)
    return os.path.join(mirror_base, rel_path)


def summary_exists(mirror_path: str) -> bool:
    """Check if a summary file already exists"""
    return os.path.exists(mirror_path)


async def summarize_file(file_element: ET.Element, current_dir: str, root_dir: str, 
                        mirror_base: str, repo_name: str, overwrite: bool, 
                        semaphore: asyncio.Semaphore) -> None:
    """Summarize a single file and save to mirror location"""
    if file_element.get('ignore', '').lower() == 'true' or \
       file_element.get('text-readable', '').lower() == 'false':
        return

    filepath = os.path.join(current_dir, file_element.get('name'))
    mirror_path = get_mirror_path(filepath, root_dir, mirror_base) + '.xml'
    
    # Skip if summary already exists
    if summary_exists(mirror_path) and not overwrite:
        log.info(f"Summary already exists for {filepath}, skipping...")
        return
    
    try:
        async with semaphore:
            file_content = read_file_to_text(filepath)
            prompt = read_file_to_text('inputs/prompts/summarize_file.md')
            prompt = replace_placeholders(prompt, {
                "{{FILEPATH}}": filepath,
                "{{FILE_NAME}}": os.path.basename(filepath),
                "{{REPO_NAME}}": repo_name,
                "{{FILE_CONTENTS}}": file_content
            })
            
            messages = [("user", prompt)]
            summary = await request_chat_completion(messages)
            
            # Create root element for the summary
            root = ET.Element('file')
            
            if "<declarations>" in summary:
                # Code file
                file_xml = extract_xml(summary, "file")
                if file_xml.startswith("<declarations"):
                    # Wrap the content in a root element before parsing
                    wrapped_xml = f"<root>{file_xml}</root>"
                    try:
                        summary_xml = ET.fromstring(wrapped_xml)
                        for child in summary_xml:
                            root.append(child)
                    except ET.ParseError as e:
                        log.error(f"Failed to parse code summary XML for {filepath}: {e}, saving entire output")
                        summary_elem = ET.SubElement(root, 'summary')
                        summary_elem.text = file_xml
            else:
                # No-code file
                summary_text = extract_xml(summary, "file-summary")
                summary_elem = ET.SubElement(root, 'file-summary')
                summary_elem.text = summary_text
            
            # Save the summary
            tree = ET.ElementTree(root)
            tree.write(mirror_path, encoding='utf-8', xml_declaration=False, method='xml')
            
    except Exception as e:
        log.error(f"Error summarizing file {filepath}: {e}")


async def process_filetree(dir_element: ET.Element, current_dir: str, root_dir: str,
                          mirror_base: str, repo_name: str, overwrite: bool,
                        semaphore: asyncio.Semaphore) -> None:
    """Process a directory and all its contents"""
    # Process all files in directory concurrently
    file_tasks = []
    for file_elem in dir_element.findall('file'):
        task = asyncio.create_task(
            summarize_file(file_elem, current_dir, root_dir, mirror_base, repo_name, overwrite, semaphore)
        )
        file_tasks.append(task)
    
    # Wait for all file summaries
    await asyncio.gather(*file_tasks)
    
    # Process subdirectories recursively
    for subdir in dir_element.findall('directory'):
        subdir_path = os.path.join(current_dir, subdir.get('name'))
        await process_filetree(subdir, subdir_path, root_dir, mirror_base, repo_name, 
                               overwrite, semaphore)


def enrich_filetree_element(element: ET.Element, current_dir: str, root_dir: str, mirror_base: str) -> None:
    """Recursively enrich the filetree by incorporating summaries"""
    # TODO make sure ignore=true is respected, and also if the filetree.xml has parts deleted
    # TODO make sure ignore=true is respected, and also if the filetree.xml has parts deleted
    # TODO make sure ignore=true is respected, and also if the filetree.xml has parts deleted
    # Process files in the current directory
    for file_elem in element.findall('file'):
        filepath = os.path.join(current_dir, file_elem.get('name'))
        mirror_path = get_mirror_path(filepath, root_dir, mirror_base) + '.xml'
        
        # If summary exists, incorporate it
        if os.path.exists(mirror_path):
            try:
                summary_tree = ET.parse(mirror_path)
                summary_root = summary_tree.getroot()
                
                # Preserve original attributes
                original_attrs = file_elem.attrib
                
                # Replace the file element's children with summary content
                file_elem.clear()
                
                # Restore original attributes
                file_elem.attrib = original_attrs
                
                # Add all children from summary
                for child in summary_root:
                    file_elem.append(child)
                    
            except ET.ParseError as e:
                log.error(f"Failed to parse summary XML for {filepath}: {e}")
        # else:
        #     ## TODO only complain about non-ignored files?
        #     log.warning(f"Summary not found for {mirror_path}")
    
    # Process subdirectories recursively
    for subdir in element.findall('directory'):
        subdir_path = os.path.join(current_dir, subdir.get('name'))
        enrich_filetree_element(subdir, subdir_path, root_dir, mirror_base)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate file and directory summaries.')
    parser.add_argument('-f', '--filetree-path', required=True,
                        help='Path to the XML filetree file.')
    parser.add_argument('-d', '--directory', required=True,
                        help='Base directory path of the repository.')
    parser.add_argument('-o', '--output',
                        help='Output directory path (default: outputs/repo_name/summaries)')
    parser.add_argument('-s', '--semaphore-size', 
                        type=int, 
                        default=DEFAULT_SEMAPHORE_SIZE,
                        help=f'Maximum number of concurrent tasks (default: {DEFAULT_SEMAPHORE_SIZE})')
    parser.add_argument('--overwrite',
                        action='store_true',
                        help='Overwrite output files if they exists')
    return parser.parse_args()


async def main():
    args = parse_arguments()
    
    # Validate inputs
    if not os.path.exists(args.filetree_path):
        raise FileNotFoundError(f"Filetree file not found: {args.filetree_path}")
    if not os.path.isdir(args.directory):
        raise NotADirectoryError(f"Directory not found: {args.directory}")
    if args.semaphore_size < 1:
        raise ValueError("Semaphore size must be at least 1")
    
    # Parse the XML filetree
    tree = ET.parse(args.filetree_path)
    root = tree.getroot()
    
    # Get repo name and create mirrored output directory
    repo_name = os.path.basename(os.path.abspath(args.directory))
    if args.output:
        mirror_base = args.output
    else:
        mirror_base = os.path.join('outputs', repo_name, 'summaries')
    create_mirrored_repo_structure(args.directory, mirror_base)
    
    # Process the entire tree and generate summaries
    semaphore = asyncio.Semaphore(args.semaphore_size)
    root_dir = args.directory  # This is our reference point for all relative paths
    await process_filetree(root, root_dir, root_dir, mirror_base, repo_name, 
                           args.overwrite, semaphore)
    
    # Enrich the filetree with summaries
    # TODO respect ignored and deleted filetree branches
    enrich_filetree_element(root, root_dir, root_dir, mirror_base)
    
    # Save the enriched filetree
    output_path = os.path.join(mirror_base, 'enriched_filetree.xml')
    tree.write(output_path, encoding='utf-8', xml_declaration=False, method='xml')
    log.info(f"Enriched filetree saved to: {output_path}")
    
    # Count tokens in the enriched filetree
    encoding = tiktoken.get_encoding("o200k_base")
    xml_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
    token_count = len(encoding.encode(xml_string))
    log.info(f"Token count of enriched filetree (o200k_base encoding): {token_count}")

if __name__ == "__main__":
    asyncio.run(main())