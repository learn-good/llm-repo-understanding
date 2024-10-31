# Using LLMs to learn about repos

<p align="center">
  <img src="media/dandadan_sakata.png" alt="Alt text" width="400">
</p>

Currently, we are using LLMs to generate a compressed representation of the repo (an XML filetree with summary information), and using that as context for future prompts. The approach is crude, limited, and more manual than I would like, but the hope is to eventually be able to make full walkthroughs, documentation, agential workflows that read entire files when necessary, etc.

# How to use
Make sure you have requirements installed (`pip install -r requirements.txt`)

## Step 1: Add Target Repository (Optional)
Place the repository you want to analyze in `./inputs/{repo_name}`. Results will be saved to `./outputs/{repo_name}/` by default.

You can add example files to the target repository if:
- The repository lacks examples
- You want to include additional examples

## Step 2: Get an XML filetree of the repo
Run `python generate_xml_filetree.py -i repo_path` to create an XML filetree (xmlft) representation of your repository's file structure. It respects .gitignore patterns by default. 

> [!TIP] 
> Use `python generate_xml_filetree.py -h` for available options. This works for the other scripts as well.

#### Basic usage
```python
# By default, input path is cwd ("."), output is saved to ./outputs/{repo_name}/filetree.xml
python generate_xml_filetree.py 

# Custom input path
python generate_xml_filetree.py -i inputs/some_repo_name
```

#### Example Output
```html
<repository name="manim">
  <file name="LICENSE.md" />
  <file name="MANIFEST.in" />
  <file name="README.md" />
  <directory name="docs">
    <file name="Makefile" />
    <file name="example.py" />
    <file name="make.bat" />
    <file name="requirements.txt" />
    <directory name="source">
      <file name="conf.py" />
      <directory name="development">
        <file name="about.rst" />
        <file name="changelog.rst" ignore="true"/>
        <file name="contributing.rst" />
      </directory>
...
```

## Step 3: Collect stats on, inspect, and edit your XML filetree
Run `python get_input_tokens_info.py -f path/to/filetree -d path/to/repo_dir` to get information about the files in the xmlft, such as token count (using `tiktoken` with `o200k_base` encoding by default), file extension count, and other info about the distribution of files that will be summarized. Ignores files and directories with `ignore="true"` in the xmlft. It also ignores counts for non-text-readable files.

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
Review the xmlft and remove or mark files you don't want analyzed. There are two ways to exclude content:

1. **Complete Removal**
   - Delete entries from `filetree.xml` to fully exclude them
   - Files won't appear in any summaries

2. **Partial Exclusion**
   - Add `ignore="true"` to entries you want to skip but keep visible
   - Example: `<directory name="somedir" ignore="true">`
   - Ignored items won't be summarized individually by LLM
   - Ignored items will still appear in the overall repo structure
   - Re-running `get_input_tokens_info.py` will skip ignored items

This helps reduce inference costs by focusing on relevant content.

## Step 4: Create summaries of files and aggregate into enriched filetree
Run `python enrich_filetree.py -f path/to/filetree.xml -d path/to/input/directory` to generate XML summaries of files and stitch them together to form an enriched filetree. `enriched_filetree.xml` will be found in the output directory if specified with `-o`, or `outputs/{repo_name}/summaries/enriched_filetree.xml` by default.

> [!NOTE] 
> This step sends async requests to generate summaries with a semaphore. Consult your provider's rate limits and send an appropriate semaphore size flag. The default size is set to 10.

## Step 5: Use the enriched filetree in your prompts 

## Limitations
- Large repos will generate huge filetrees. You will have to process subdirectories of those repos.
- This workflow still requires a lot of manual involvement from the user, e.g., for trimming the filetree.
- As with any LLM endeavor, there is hallucination risk, so summaries can be incorrect or incomplete.
- The LLM may produce summaries in a non-parsable format.
- `request_chat_completion` uses the `AsyncAnthropic` client, and currently doesn't support anything else.
- The XML indenting isn't always great, especially for python<3.9 and for the enriched filetree.

<!-- ## Would appreciate community feedback on:
- Does using the enriched filetree in your prompts lead to better results?
- Are there better alternative approaches to summarizing a repo? (better prompt variations, XML structure, etc.)
- Have you found a good way (prompting techniques, chains of prompts, etc.) to generate an effective human-readable walkthrough, guide, etc. for code repos?
- Does adding working examples to the repo help, or is it unnecessary? -->