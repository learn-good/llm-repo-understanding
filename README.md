# Using LLMs to learn about repos

<p align="center">
  <img src="media/dandadan_sakata.png" alt="Alt text" width="400">
</p>

This is an attempt at using LLMs to help understand a repo by performing a DFS-style traversal of a repository's filetree: leaf nodes (files) and subtrees are summarized prior to creating a summary of the parent. 

After one pass enriching the file tree with relevant information, attempt to summarize the repo in either a "text" form, which will be structured markdown, or "speech" form, which can serve as input to a text-to-speech API or used to provide a textual narrative overview of the repo. 

# How to use
Make sure you have requirements installed (`pip install -r requirements.txt`)

## Step 1 (Optional): Add Target Repository
Place the repository you want to analyze in `./inputs/{repo_name}`. You can alternatively specify the repository path directly as an input argument. Results will be saved to `./outputs/{repo_name}/` by default.

You can add example files to the target repository if:
- The repository lacks examples
- You want to include additional examples

## Step 2: Get an XML filetree of the repo
Run `python generate_xml_filetree.py -i repo_path` to create an XML filetree representation of your repository's file structure. It respects .gitignore patterns by default. 

> [!TIP] 
> Use `python generate_xml_filetree.py -h` for available options.

#### Basic usage
```
# By default, input path is cwd ("."), output is saved to ./outputs/{repo_name}/filetree.xml
python generate_xml_filetree.py 

# Custom input/output paths
python generate_xml_filetree.py -i /path/to/repo_name -o /path/to/out/ft.xml
```

#### Example Output
html ```
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
Run `python get_input_tokens_info.py -f path/to/filetree -d path/to/repo_dir` to get information about the files in the filetree, such as token count (using `tiktoken` with `o200k_base` encoding), file extension count, and other info about the distribution of files that will be summarized. Ignores files and directories with `ignore="true"` in the filetree or are not text readable.

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



------------

## Step 4: Enrich the filetree with file and directory summaries
DFS traversal over filetree:
- Make a copy of the filetree called `enriched_filetree.xml`
- Whenever a file is sumarized, you can write out its contents to replace a leaf  for the original filetree (use `enriched_filetree`)
- Whenever all the descendants of a directory are summarized, the containg directory gets summarized in


<directory name="custom_commands">
    <directory-summary>
        <!-- Describe what this directory and containing files accomplishes, how these should be used, etc -->
    </directory-summary>
    <file name="ManimCheckpointPaste.sublime-commands" />
    ...
    <file name="manim_plugins.py" />
</directory>
(this one is an append inside rather that a total replace)

**TODO** decide what the prompt is for a leaf
- feed in filetree skeleton
- feed in name of the repo
- get formatted response
<file name="example-file">
    <declarations> 
        <!-- declared variables and constants (at the file level, not scope to functions) -->
    </declarations>
    <dependencies>
        <external> 
            <!-- Dependencies that are not native to the repo -->
        </external>
        <internal> 
            <!-- Dependencies that are not native to the repo -->
        </internal>
    </dependencies>
    <function-defs>
        <function name="The name should be the function signature, not just the name, e.g. `is_even(n: number) -> bool`">
            <description>
                <!-- Describe the function consicely -->
            </description>
            <args></args>
            <returns></returns>
            <side-effects>
                <!-- any side effects outside the functions scope? -->
            </side-effects>
            <errors-and-exceptions>
                <handled></handled>
                <unhandled>
                    <!-- errors that the code does not have error handling, but probably should -->
                </unhandled>
            </errors-and-exceptions>
        </function>
        <function name="some_other_fn(h) -> List[Dict]">
            ...
        </function>
    </function-defs>
    <file-summary>
        <!-- If file is not code, but instead just plaintext, this is the only section needed -->
        <!-- Also need to be present for code files, too -->
    </file-summary>
</file>

**TODO** decide what the prompt is for a parent
- feed in completed subtree


run `python enrich_xml_filetree.py` to perform a depth first traversal over the repo 
- Optional arg: --batch (to save 50% with Anthropic. We'll just use Sonnet 3.5)


- This will summarize the files in the directory first, and then use those summaries to characterize the directory. (make sure `ignore="true"` property is respected)
  - Files in the same dir can get processed together ASYNC
  - (Optional arg): `--gen-readme` to generate README.md in each of the sub repos. If the root or any other dir already has a README.md, generate README2.md
- Files get summarized by: (all of these are "minimal" in the sense that if they are not there, don't include empty tags. LLM can do it for regularity, but they should be parsed out in later pass)
  - declarations
    - variables
    - constants
  - dependencies 
    - external to repo
    - internal links (give exact paths for these because we may have to reference on second pass)
  - function defs
    - function (attribute signature)
      - description
      - args
      - returns
      - side effects
      - throws
        - handled
        - unhandled
  - notes / caution (Give a short gist of what the file is and what it does. Is there anything to be aware of, potential problems, stated and unstated assumptions or expectations?)
- Repo gets summarized by feeding its files XMLs as contextual input.





------------


## Step 5: run `python generate_repo_explanation.py`
- Output Options: `script` ("read aloud") for a voice API or `markdown`
  - Need 2 diff prompts, output parsers and handlers for this
- **User should be able to give custom instructions at this step**. You might care about a specific use case, have a particular end goal, or want to specify your current understanding, etc., so you should be able to tailor the output if you choose.
- Required Sections in the script:
  - Repo Overview: What does this repo accomplish? What are the common tasks and use cases for this repo? What are some idiosyncrasies about this repo? Are there nomenclature, acronyms, etc. used in the code or documentation that the reader might not know (explain if so)? Are there any examples in this repo I could look at? How is this repo/tool the same and different from other repos or tools that are in the space?
  - Repo main components: What are the main "areas" or component systems of this repo? `for each` of these:
    - Are there any specific naming or code conventions adopted (explain if so)? Is there any nomenclature, acronyms, etc. used in this section the user might not know (explain if so)? How is this area or component system used in other areas of the codebase? What are the key abstractions used? List and explain the core components.
  - Setup: Any requirements.txt? Does it require any env variables to be set? Any dependencies? Any operating system specific requirements? Make sure the setup steps are straighforward and spelled out.
  - Practical application: What can I do with this repo now? If there is examples in the repo already, mention where they are, and describe them. Give one instructive example in detail.

