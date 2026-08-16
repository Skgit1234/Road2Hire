# Literature Review

## 1. Skill-Gap Identification Systems
### Paper 1 — Large-Scale Occupational Skills Normalization for Online Recruitment

* **Authors/Year:** Faizan Javed, Phuong Hoang, Thomas Mahoney, and Matt McNair (2017)
* **Problem:** The paper addresses the difficulty of accurately identifying and normalizing occupational skills from resumes and online job advertisements. Accurate skill identification is important for understanding the relationship between workers' skills and employer requirements.
* **Approach:** The authors developed SKILL, a Named Entity Normalization system for occupational skills. It uses semantic word vectors for skill tagging and a sense-disambiguation component based on Markov Chain Monte Carlo (MCMC).
* **Key Finding:** The system achieved 90% precision and 73% recall for skill tagging and demonstrated applications in semantic search, job matching, workforce analytics, and recommendations.
* **Limitation:** The work mainly focuses on skill extraction and normalization. It does not provide a complete candidate-specific skill-gap analysis or integrate career prediction, knowledge graphs, explainable AI, and personalized RAG-based learning recommendations. Road2Hire aims to extend skill extraction into a complete personalized career-guidance pipeline.

### Paper 2 — Illustrating the Application of a Skills Taxonomy, Machine Learning and Online Data to Inform Career and Training Decisions

* **Authors/Year:** Claire M. Mason, Haohui Chen, David Evans, and Gavin Walker (2023)
* **Problem:** The study addresses the gap between the skills possessed or supplied by workers and graduates and the skills demanded by employers. It aims to use this information to support career and training decisions.
* **Approach:** The researchers combine the ESCO skills taxonomy, natural language processing, machine learning, and online data from job advertisements, course descriptions, and resumes to identify and compare skills.
* **Key Finding:** The approach demonstrates that combining skills data from different sources can identify skill gaps and support career-path and training decisions.
* **Limitation:** The study focuses mainly on identifying skill gaps and informing career and training decisions. It does not provide Road2Hire's complete pipeline combining candidate-specific semantic skill matching, knowledge-graph reasoning, career prediction, explainable AI, and personalized RAG.

### Paper 3 — A Combined Representation Learning Approach for Better Job and Skill Recommendation

* **Authors/Year:** Vachik S. Dave, Baichuan Zhang, Mohammad Al Hasan, Khalifeh AlJadda, and Mohammed Korayem (2018)
* **Problem:** The study addresses the challenge of recommending suitable jobs and identifying additional skills that may be needed when people transition between jobs.
* **Approach:** The authors construct three interconnected networks: a job-transition network, a job-skill network, and a skill co-occurrence network. Representation learning is then used to learn relationships between jobs and skills in a shared latent space.
* **Key Finding:** Combining job-transition, job-skill, and skill co-occurrence information improves job and skill recommendations and can identify additional skills relevant to a target job.
* **Limitation:** The system focuses primarily on job and skill recommendation rather than detailed, candidate-specific skill-gap explanation. It does not integrate resume-based semantic matching, an explicit knowledge graph, explainable AI, or personalized RAG-based learning recommendations. Road2Hire can extend these ideas toward personalized and explainable career guidance.

### Paper 4 — Skill-driven Recommendations for Job Transition Pathways

* **Authors/Year:** Alexandra Dawson, Michael Rizoiu, and colleagues (2021)
* **Problem:** The study addresses the difficulty of identifying suitable career transitions and estimating the skill gap between a person's current occupation and a potential target occupation.
* **Approach:** The researchers introduce a Skills Space methodology that measures the distance between occupational skill sets. They use more than 8 million Australian job advertisements and combine skill-distance information with employment and labour-market data to recommend job transition pathways.
* **Key Finding:** The approach can quantify the similarity and distance between occupations and help identify potentially suitable career transitions. The resulting recommender achieved 76% accuracy in predicting occupational transitions.
* **Limitation:** The approach primarily works with occupational skill sets and labour-market data rather than directly analyzing an individual candidate's resume. It also does not provide detailed explanations of individual skill gaps or integrate personalized learning recommendations, knowledge-graph reasoning, explainable AI, or RAG.

## 2. Resume NLP and Skill Extraction

## 3. Semantic Skill Matching

## 4. Knowledge Graphs for Career Guidance

## 5. Career Prediction and Recommendation

## 6. Explainable AI for Career Recommendation

## 7. Personalized Retrieval-Augmented Generation (RAG)
