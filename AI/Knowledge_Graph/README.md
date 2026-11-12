\# Knowledge Graph V1



\## Objective



Use the Road2Hire skill graph to identify direct skill matches, relationship-based matches, and missing target skills.



\## Components



\- `skill\_graph\_v1.json` — graph nodes and directed relationships.

\- `skill\_graph\_matcher.py` — graph loading, skill matching, and relationship evidence.

\- `graph\_evaluation\_data.json` — manually specified evaluation cases.

\- `evaluate\_skill\_graph.py` — evaluation runner and metrics.

\- `graph\_evaluation\_results.json` — generated evaluation report.

\- `visualize\_skill\_graph.py` — generates a Graphviz DOT representation.

\- `skill\_graph\_v1.dot` — generated visualization source.



\## Matching Behavior



\- Direct matches require the same recognized graph skill.

\- Related matches use explicit graph relationships.

\- Relationship evidence preserves the relationship type and direction.

\- Unknown skills are reported separately and are not automatically inserted into the graph.

\- Recognized skills with no applicable relationship are reported separately.

\- Related skills are not assumed to be equivalent to required skills.



\## Current Graph



The graph contains nine skills and four directed relationships:



\- Machine Learning `requires` Python.

\- Machine Learning `related-to` Scikit-learn.

\- Python `related-to` NumPy.

\- Python `related-to` Pandas.



The current graph does not contain `equivalent` or `prerequisite` relationships.



\## Evaluation



Run:



`python AI\\Knowledge\_Graph\\evaluate\_skill\_graph.py`



The initial manually specified evaluation dataset contains four cases. The current evaluation reports 16/16 expected-result checks passing.



Precision, recall, and F1 are calculated separately for direct matches and relationship-based matches. These results are preliminary and should not be interpreted as real-world performance measurements.



NDCG is not calculated because this implementation does not produce a ranked list of skills.



\## Visualization



Run:



`python AI\\Knowledge\_Graph\\visualize\_skill\_graph.py`



The script generates `skill\_graph\_v1.dot` from the JSON graph. Graphviz can render this file into an image when installed.



\## Limitations



\- The graph is small and uses manually defined relationships.

\- Matching uses graph skill names and case/whitespace normalization.

\- Related matches are evidence of a relationship, not proof of skill equivalence or proficiency.

\- Baseline comparisons and larger, independently labeled evaluation datasets remain necessary.

\- Unknown skills remain available to other matching methods; they are not automatically added to the graph.



