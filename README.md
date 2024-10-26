# Using LLMs to learn about repos

<p align="center">
  <img src="media/dandadan_sakata.png" alt="Alt text" width="400">
</p>

This is an attempt at using LLMs to help understand a repo by performing a DFS-style traversal of a repository's filetree: leaf nodes (files) and subtrees are summarized prior to creating a summary of the parent. 

After one pass enriching the file tree with relevant information, attempt to summarize the repo in either a "text" form, which will be structured markdown, or "speech" form, which can serve as input to a text-to-speech API or used to provide a textual narrative overview of the repo. 

# How to use
Make sure you have requirements installed (`pip install -r requirements.txt`)

## Step 1: Add Target Repository (Optional)
Place the repository you want to analyze in `./inputs/{repo_name}`. Results will be saved to `./outputs/{repo_name}/` by default.

You can add example files to the target repository if:
- The repository lacks examples
- You want to include additional examples

## Step 2: Get an XML filetree of the repo
Run `python generate_xml_filetree.py -i repo_path` to create an XML filetree representation of your repository's file structure. It respects .gitignore patterns by default. 

> [!TIP] 
> Use `python generate_xml_filetree.py -h` for available options.

#### Basic usage
```python
# By default, input path is cwd ("."), output is saved to ./outputs/{repo_name}/filetree.xml
python generate_xml_filetree.py 

# Custom input path
python generate_xml_filetree.py -i inputs/some_repo_name
```

#### Example Output
```html
<repository name="llm-repo-understanding">
  <file name="LICENSE" />
  <file name="README.md" />
  <file name="enrich_filetree.py" />
  <file name="generate_xml_filetree.py" />
  <file name="get_input_tokens_info.py" />
  <directory name="outputs">
    <directory name="llm-repo-understanding">
      <file name="filetree.xml" />
    </directory>
    <directory name="manim">
      <file name="filetree.xml" />
    </directory>
  </directory>
  <file name="requirements.txt" />
</repository>
```

## Step 3: Collect stats on, inspect, and edit your XML filetree
Run `python get_input_tokens_info.py -f path/to/filetree -d path/to/repo_dir` to get information about the files in the filetree, such as token count (using `tiktoken` with `o200k_base` encoding), file extension count, and other info about the distribution of files that will be summarized. Ignores files and directories with `ignore="true"` in the filetree. It also ignores counts for non-text-readable files.

Example output:
```
$ python get_input_tokens_info.py -d inputs/manim -f outputs/manim/filetree.xml

=== Statistics ===
Total files: 233
Total directories: 54
Total file content tokens: 785021

Token Statistics:
Mean tokens per file: 3369.19
Median tokens per file: 977
Max tokens: 39764

=== Largeset Files (by token count) ===
39,764 tokens: inputs/manim/videos/_2024/holograms/diffraction.py
37,090 tokens: inputs/manim/videos/_2024/transformers/attention.py
30,554 tokens: inputs/manim/videos/_2023/clt/main.py
26,101 tokens: inputs/manim/videos/_2024/transformers/embedding.py
24,330 tokens: inputs/manim/videos/_2024/transformers/mlp.py

File type distribution:
  .py: 166 files
  .glsl: 30 files
  .rst: 17 files
...
```

#### Customize File Selection
Review the output filetree and remove or mark files you don't want analyzed. There are two ways to exclude content:

1. **Complete Removal**
   - Delete entries from filetree.xml to fully exclude them
   - Files won't appear in any summaries

2. **Partial Exclusion**
   - Add `ignore="true"` to entries you want to skip but keep visible
   - Example: `<directory name="somedir" ignore="true">`
   - Ignored items won't be summarized individually
   - Ignored items will still appear in the overall repo structure
   - `get_input_tokens_info.py` will skip ignored items

This helps reduce processing costs by focusing on relevant content.

## Step 4: Enrich the filetree with file and directory summaries
