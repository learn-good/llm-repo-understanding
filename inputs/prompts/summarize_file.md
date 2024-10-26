[Task Overview]
We are analyzing a file {{FILEPATH}}, name={{FILE_NAME}}, in the {{REPO_NAME}} repository.
The goal is to extract information from the file into structured XML with predefined tags.

[Formatting instructions]
I am providing a template for how to handle files with and without code.
For files with no code, we just create a summary of the file.
For files with code, we extract specific information about the file, such as constant/variables declarations, function declarations, and dependencies.
Failure to respond with one of the two templates will result in a parsing error and immediate disqualification.
Even if there is nothing to fill out for a particular tag, for example, a function with no return value, the opening and closing tag (<returns></returns>) must still be present, just with no information inside.

[Response Template 1]
<file name="example-file-no-code"> 
    <file-summary>
        <!-- This is the only section needed if no code -->
    </file-summary>
</file>

[Response Template 2]
<file name="example-file-code">
    <declarations> 
        <!-- declared variables and constants (at the file level, not scoped to functions) -->
    </declarations>
    <dependencies>
        <external> 
            <!-- Dependencies that are not native to the repo -->
        </external>
        <internal> 
            <!-- Dependencies that are native to the repo -->
            <filepath>
                <!-- Filepath relative to the file, e.g., `../utils/vision.py` -->
            </filepath>
            <description>
                <!-- How is this dependency used in the file? What end does it accomplish? -->
            </description>
        </internal>
    </dependencies>
    <function-defs>
        <function name="is_even">
            <description>
                <!-- Describe the function consicely -->
            </description>
            <args>
                <!-- Describe function arguments and their types -->
            </args>
            <returns>
                <!-- Describe type of returned value(s) -->
            </returns>
            <side-effects>
                <!-- Any side effects on things outside the functions scope? -->
            </side-effects>
            <errors-and-exceptions>
                <handled>
                    <!-- Caught and handled errors or exceptions -->
                </handled>
                <unhandled>
                    <!-- errors that the code does not have error handling, but probably should -->
                </unhandled>
            </errors-and-exceptions>
        </function>
        <function name="some_other_fn">
            ...
        </function>
    </function-defs>
    <file-summary>
    </file-summary>
</file>

[File contents]
{{FILE_CONTENTS}}