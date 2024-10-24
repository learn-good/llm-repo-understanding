# Using LLMs to learn about repos

This is an attempt at using LLMs to help understand a repo by performing a DFS-style traversal of the filetree: leaf nodes (files) and subtrees are summarized prior to creating a summary of the parent. 

After one pass enriching the file tree with relevant information, attempt to summarize the repo in either a "text" form, which will use markdown, or "speech" form, which can serve as input to a text-to-speech API or as a textual narrative overview of the repo. *(TODO later: potentially include second pass later prior to repo summary)*

# How to use

## *(TODO requirements.txt)*

## Step 1 (Optional): Place your target repo in this directory
Place the target repo (the repo you want to learn more about) into this directory, e.g. `./inputs/{repo_name}`. Outputs will go to `./outputs/{repo_name}/some_output` by default. This step is optional because you can just point to the repo as an input argument, but this is just an organizational suggestion. 

You may also want to drop (hopefully working) examples into the target repo, if they don't have it already, or if you want to provide additional examples. For `manim` I dropped videos from the 3b1b channel videos repo, `videos`.

## Step 2: Get an XML filetree (xmlft) of the repo
Run `python generate_xml_filetree.py -i repo_path` to create an XML representation of your repository's file structure. It respects .gitignore patterns and identifies binary files. 

> [!TIP] 
> Use `python generate_xml_filetree.py -h` for available options.

#### Basic usage
```
# By default, input path is cwd (".'), output is saved to ./outputs/{repo_name}/filetree.xml
python generate_xml_filetree.py 

# Custom input/output paths
python generate_xml_filetree.py -i /path/to/repo_name -o /path/to/out/ft.xml
```

## Step 3: Collect stats on, inspect, and edit your XML filetree
Run `python get_input_tokens_info.py -f path/to/filetree -d path/to/repo_dir` to get information about the files in the filetree, such as token count, file extension count, and other info about the distribution of files that will be summarized. Ignores files and directories with `ignore="true"` in the filetree or are not text readable.

Example output:
```
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

Make sure all entries in the output filetree are things you want to read and summarized by the LLM. You can exclude subdirectories or files perceived to be of low informational value to save a bit of expense.

Manually delete parts of the filetree.xml to completely exclude the files or directories from the final output, or add `ignore="true"` to files and directories that you do not wish to summarize, but want to keep in the filetree skeleton for the overall repo summarization (e.g., `<directory name="somedir" ignore="true">` will ignore the `path/to/somedir` directory and comprising subdirectories and files when summarizing individual files and directories, but the final repo summarization step will be able to see that those files exist in the filetree). `get_input_tokens_info.py` will also ignore files with `ignore="true"` for counting.

## Step 4: Enrich the filetree with file and directory summaries

DFS
run `python enrich_xml_filetree.py` to perform a depth first traversal over the repo 



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

## Step 5b?: run `python second_pass_enrich_xml_filetree.py` (optional, might skip this for now)
- more detail

## Step 6: run `python generate_repo_explanation.py`
- Output Options: `script` ("read aloud") for a voice API or `markdown`
  - Need 2 diff prompts, output parsers and handlers for this
- **User should be able to give custom instructions at this step**. You might care about a specific use case, have a particular end goal, or want to specify your current understanding, etc., so you should be able to tailor the output if you choose.
- Required Sections in the script:
  - Repo Overview: What does this repo accomplish? What are the common tasks and use cases for this repo? What are some idiosyncrasies about this repo? Are there nomenclature, acronyms, etc. used in the code or documentation that the reader might not know (explain if so)? Are there any examples in this repo I could look at? How is this repo/tool the same and different from other repos or tools that are in the space?
  - Repo main components: What are the main "areas" or component systems of this repo? `for each` of these:
    - Are there any specific naming or code conventions adopted (explain if so)? Is there any nomenclature, acronyms, etc. used in this section the user might not know (explain if so)? How is this area or component system used in other areas of the codebase? What are the key abstractions used? List and explain the core components.
  - Setup: Any requirements.txt? Does it require any env variables to be set? Any dependencies? Any operating system specific requirements? Make sure the setup steps are straighforward and spelled out.
  - Practical application: What can I do with this repo now? If there is examples in the repo already, mention where they are, and describe them. Give one instructive example in detail.

# Test with
- manim
- entropix


---------

#### Note `inputs` are for input repos (should be added to .gitignore for space)
#### `outputs` can be tracked

#### TODO experiment with README.md in vs out

#### TODO how to setup split tests for prompt variations, different combos of underlying models, etc.

## TODO for speech generation, add "cues", which will be special xml that is parsed before TTS, to 
## indicate a time a certain section starts. Hopefully with timing info from the TTS response (elevenlabs has this at a character or phoneme level), we can create/sync video to it
- If not this way maybe lossy translation back from speech to text with timestamps to find/insert cues for scene change

## TODO - add inputs/example input dir and outputs/example run and 