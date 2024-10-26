import os
import xml.etree.ElementTree as ET
import argparse
import asyncio
from utils import request_chat_completion, extract_xml, read_file_to_text, replace_placeholders, log
from typing import Tuple

SEMAPHORE_SIZE = 10

async def summarize_file(file_element: ET.Element, base_dir: str, repo_name: str, 
                         semaphore: asyncio.Semaphore) -> Tuple[str, str]:
    """Summarize a single file using the LLM"""
    if file_element.get('ignore', '').lower() == 'true' or \
       file_element.get('text-readable', '').lower() == 'false':
        return "", ""

    # Reconstruct full filepath
    filepath = os.path.join(base_dir, file_element.get('name'))
    
    try:
        async with semaphore:  # Use semaphore to limit concurrent requests
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
            
            # Extract either code or no-code summary based on response
            if "<declarations>" in summary:
                # Code file - extract all relevant sections
                file_xml = extract_xml(summary, "file")
                
                if file_xml.startswith("<declarations"):
                    return file_xml, "code"
                else:
                    log.warning("Could not detect <declarations...")
                    return "", ""
            else:
                # No-code file
                return extract_xml(summary, "file-summary"), "nocode"
                
    except Exception as e:
        log.error(f"Error summarizing file {filepath}: {e}")
        return "", ""


async def summarize_directory(dir_element: ET.Element, base_dir: str, repo_name: str, 
                              semaphore: asyncio.Semaphore) -> str:
    """Summarize a directory using the LLM based on its contents"""
    if dir_element.get('ignore', '').lower() == 'true':
        return ""
        
    dir_name = dir_element.get('name')
    dir_path = os.path.join(base_dir, dir_name) if dir_name else base_dir
    
    try:
        async with semaphore:  # Use semaphore to limit concurrent requests
            filetree_branch = ET.tostring(dir_element, encoding='unicode', method='xml')
            prompt = read_file_to_text('inputs/prompts/summarize_directory.md')
            prompt = replace_placeholders(prompt, {
                "{{FILEPATH}}": dir_path,
                "{{DIR_NAME}}": os.path.basename(dir_path),
                "{{REPO_NAME}}": repo_name,
                "{{FILETREE_BRANCH}}": filetree_branch
            })
            
            messages = [("user", prompt)]
            summary = await request_chat_completion(messages)
            return extract_xml(summary, "directory-summary")
        
    except Exception as e:
        log.error(f"Error summarizing directory {dir_path}: {e}")
        return ""


async def process_filetree(dir_element: ET.Element, base_dir: str, repo_name: str,
                           semaphore: asyncio.Semaphore) -> None:
    """Process a directory and all its contents"""
    # Process all files in directory concurrently
    file_tasks = []
    for file_elem in dir_element.findall('file'):
        task = asyncio.create_task(summarize_file(file_elem, base_dir, repo_name, semaphore))
        file_tasks.append((file_elem, task))
    
    # Wait for all file summaries
    for file_elem, task in file_tasks:
        summary, file_type = await task
        if summary:
            if file_type == "code":
                # Wrap the content in a root element before parsing
                wrapped_xml = f"<root>{summary}</root>"
                try:
                    summary_xml = ET.fromstring(wrapped_xml)
                    # Copy all child elements from the summary to the file element
                    for child in summary_xml:
                        file_elem.append(child)
                except ET.ParseError as e:
                    log.error(f"Failed to parse code summary XML: {e}")
                    # Fallback: create simple summary tag and put everything inside
                    summary_elem = ET.SubElement(file_elem, 'summary')
                    summary_elem.text = summary
            else:  # file_type == "nocode"
                # Create simple file-summary tag for non-code files
                summary_elem = ET.SubElement(file_elem, 'file-summary')
                summary_elem.text = summary
    
    # Process subdirectories recursively
    for subdir in dir_element.findall('directory'):
        subdir_path = os.path.join(base_dir, subdir.get('name'))
        await process_filetree(subdir, subdir_path, repo_name, semaphore)
        
    # After processing all contents, summarize the directory itself
    if dir_element.tag != 'repository':  # Skip summarizing the root
        summary = await summarize_directory(dir_element, base_dir, repo_name, semaphore)
        if summary:
            # Create a properly structured directory summary
            # First, check if there's an existing summary element
            existing_summary = dir_element.find('summary')
            if existing_summary is not None:
                dir_element.remove(existing_summary)
            
            # Create new summary element with proper structure
            summary_elem = ET.Element('directory-summary')
            summary_elem.text = summary
            
            # Insert the summary element as the first child
            dir_element.insert(0, summary_elem)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Enrich XML filetree with summaries.')
    parser.add_argument('-f', '--filetree-path', required=True,
                        help='Path to the XML filetree file.')
    parser.add_argument('-d', '--directory', required=True,
                        help='Base directory path of the repository.')
    return parser.parse_args()

async def main():
    args = parse_arguments()
    
    # Validate inputs
    if not os.path.exists(args.filetree_path):
        raise FileNotFoundError(f"Filetree file not found: {args.filetree_path}")
    if not os.path.isdir(args.directory):
        raise NotADirectoryError(f"Directory not found: {args.directory}")
    
    # Parse the XML filetree
    tree = ET.parse(args.filetree_path)
    root = tree.getroot()
    
    # Get repo name from directory path
    repo_name = os.path.basename(os.path.abspath(args.directory))
    
    # Process the entire tree
    semaphore = asyncio.Semaphore(SEMAPHORE_SIZE)
    await process_filetree(root, args.directory, repo_name, semaphore)
    
    # Save enriched filetree
    output_dir = os.path.dirname(args.filetree_path)
    output_path = os.path.join(output_dir, 'enriched_filetree.xml')
    
    # Save enriched xml
    tree.write(output_path, encoding='utf-8', xml_declaration=False)
    print(f"Enriched filetree saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
