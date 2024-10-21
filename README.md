# Using LLMs to learn about repos

This is an attempt at using LLMs to help understand a repo by performing a DFS-style traversal of the filetree: leaf nodes (files) and subtrees are summarized first, before creating a summary of the parent. After one pass enriching the file tree with relevant information, attempt to summarize the repo in either a "text" form, which will use markdown, or "speech" form, which can serve as input to a text-to-speech API.

# How to use

## Step 1: run `python generate_xml_filetree.py` to get the XML filetree (xmlft) of the repo
- Uses .gitignore to decide which files to skip over. Also skips over hidden files (`.*`)
- TODO: document args usage
- TODO: Add more to the auto-ignore list: images, videos, ask LLM to get a decent seed list
  - TODO make it clear what is excluded
- TODO: should ignore itself `generate_xml_filetree.py, _xmlft_*` by default
- TODO: (maybe later): Check `_xmlft_ignore.txt` (like .gitignore but explicit) and `_xmlft_include.txt` (only include anything that matches this) for more control

## Step 2: inspect and edit output of step 1
- Make sure everything that is in the output file tree are things you want to learn about
  - Will cost tokens to process, so you want to make sure you're not reading in things like SVGs, PNGs, low info subdirectories, etc.
  - Either delete parts of the tree to remove the sections entirely from the final output, or add `inspected="false"` to files and directories that we do not want to summarize, but want to keep in the skeleton for summarization later.
  - You might also want to drop (hopefully working) examples into the target repo, if they don't have it already. For example, for manim I dropped videos from the 3b1b channel videos repo.

## Step 3: run `python xmlft_tokens_info.py`to get information
- Assume everything (filename + file contents) is read exactly once, call that the lower bound for input tokens (ignore `inspected="false"` files and directories)
- Use tiktoken library to get token count of (all filenames + all file contents)
- Should also report/warn of individual files that have exceeded certain token size thresholds (May result in error or have otherwise outlier behavior. Make sure it fits in your chosen LLM's context window and consider that the LLM may keep the output short and avoid reproducing the appropriate level of detail for these larger files. Maybe someone will come up with a good way to navigate these?)
  - 8K, 16K, 32K, 64K, 128K
- Give distribution (histogram) of file input tokens
- Give filename extension count
- Give estimated lower bound input in terms of millions of tokens

## Step 3b: run `python enrich_xml_filetree.py` to perform a depth first traversal over the repo 
- This will summarize the files in the directory first, and then use those summaries to characterize the directory. (make sure `inspected="false"` property is respected)
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

## Step 3b: run `python second_pass_enrich_xml_filetree.py` (optional, might skip this for now)
- more detail

## Step 4: run `python generate_repo_explanation.py`
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

#### Note `inputs` are for input repos (should be added to .gitignore for space)
#### `outputs` can be tracked

#### TODO experiment with README.md in vs out