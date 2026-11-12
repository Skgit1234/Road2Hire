Keyword Matching Baseline
Objective

The keyword matching baseline provides a simple reference method for identifying whether candidate skills match the skills required by a job.

It will serve as the baseline for comparison with future skill matching and Hybrid Skill Gap Detection methods.

Method

The baseline:

Reads candidate skills.

Reads required job skills.

Converts skill names to lowercase for case-insensitive matching.

Checks whether each required skill exists in the candidate skill list.

Identifies present skills.

Identifies missing skills.

Calculates a basic match score.

Match Score

The match score is calculated as:

Match Score = Number of Present Required Skills / Total Required Skills

Sample Results
Evaluation	Present Skills	Missing Skills	Match Score
EVAL001	Python, Pandas	Scikit-learn, Machine Learning	0.50
EVAL002	Python, Machine Learning, Scikit-learn	None	1.00
EVAL003	JavaScript, React	Python	0.67
Limitations

The keyword baseline has several limitations:

Exact skill names are required for matching.

Synonyms and aliases are not handled.

Skill relationships are not considered.

Skill hierarchy is not considered.

Context of skills is not considered.

Similar or related skills may be incorrectly treated as missing.

Spelling variations may cause mismatches.

The method does not understand the proficiency level of a skill.

The method does not use the Knowledge Graph relationships.

Future Comparison

Future skill matching methods will be compared against this baseline using the same evaluation samples.

The comparison can consider:

Skill matching accuracy

Present skill identification

Missing skill identification

Match score

Handling of aliases and related skills

Handling of Knowledge Graph relationships

Baseline Version

Keyword Matching Baseline: V1