**SAFEJUDGE**

*Runtime Tool-Call Governance for LLM Agents*

 

| Mode | Implementation-Heavy |
| :---- | :---- |
| **Team** | Aaron Sweeny \- Juan Martin Zambrano Lozano |

|   | *SafeJudge builds a structured evaluation and validation layer on top of an existing AI safety classifier (analyze-prompt-intent) to systematically measure classification accuracy, consistency, and robustness, then surfaces those metrics through dashboards and release gates.* |
| :---- | :---- |

 [SafeJudge Multi-Model LLM-as-a-Judge for Automated AI Safety Evaluation.pptx](https://docs.google.com/presentation/d/1f4dTlxaFpaO6TtWWTTOsKVtUpqNgdKOm/edit?usp=share_link&rtpof=true&sd=true)

[ME575 Project Video.mp4](https://drive.google.com/file/d/1N-nyjqAGstYgiR6jJ5W4pxu_pIANe5Gi/view?usp=share_link)

| 1 | Project Title and Mode |
| :---: | :---- |

 

**Project Title:** SafeJudge \- Implementation of a Multi-Model LLM-as-a-Judge Variant for Automated AI Safety and Risk Evaluation

**Mode:** Implementation-Heavy

 

|   | *Implementation-Heavy: This project builds a structured evaluation and validation layer on top of an existing AI safety classification system (analyze-prompt-intent). The focus is on implementing an LLM-as-a-Judge evaluation pipeline that systematically measures classification accuracy, consistency, and robustness, then surfaces those metrics through dashboards, release gates, and documented controls.* |
| :---- | :---- |

| 2 | Problem Context |
| :---: | :---- |

   
Organizations deploying LLM-based safety classifiers face a fundamental challenge: how do you know the classifier is working correctly? A prompt safety analyzer may produce structured JSON outputs claiming a prompt is safe or malicious, but without systematic evaluation, teams cannot answer critical questions:

- **Accuracy:** Does the classifier correctly identify jailbreak attempts, prompt injections, and harmful content?  
- **Consistency:** Does the same prompt produce the same classification across repeated runs, different models, or slight prompt variations?  
- **Robustness:** Can adversarial inputs fool the classifier? Do obfuscation techniques (Base64, ROT13, leetspeak, Unicode escapes) successfully evade detection?  
- **False positive rate:** Does the classifier incorrectly flag legitimate educational, security research, or benign queries?  
- **Drift:** As models are updated or swapped (e.g., moving from gpt-oss to qwen3), do classification behaviors shift?

Without answers to these questions, deploying a safety classifier creates a false sense of security. The system may pass manual spot checks while consistently failing on entire categories of attack. This is the type of silent failure discussed in class: the system runs, outputs are produced, but the quality of those outputs degrades without any visible error signal.

This project addresses the operational risk gap between "we have a safety classifier" and "we have evidence that our safety classifier works, and we know when it stops working."

| 3 | Target Entity / Use Case |
| :---: | :---- |

   
**Entity:** A mid-size technology company deploying an internal AI assistant (chatbot) for employee use across HR, IT support, and knowledge management functions.

**Users and stakeholders:**

| Stakeholder | Role |
| :---- | :---- |
| AI/ML Engineering Team | Builds and maintains the safety classifier; needs metrics to validate model changes |
| Security Team | Requires assurance that the classifier catches prompt injection and jailbreak attempts |
| Compliance Officer | Needs audit-ready evidence that safety controls are tested and functioning |
| Product Manager | Needs confidence that the assistant will not produce harmful outputs to employees |
| End Users (Employees) | Expect the assistant to be both helpful and safe |

**Scenario:** Before promoting a new model version or updated classifier configuration to production, the engineering team must run the evaluation pipeline and demonstrate that classification performance meets defined thresholds. The pipeline produces artifacts (test results, dashboards, metric reports) that serve as evidence for compliance review.

| 4 | System Scope |
| :---: | :---- |

 

System Under Test  
The system under evaluation is [analyze-prompt-intent](https://github.com/ajsween/analyze-prompt-intent), an existing Python-based prompt safety analyzer. It classifies user prompts across three threat dimensions:

- **Jailbreak detection** \-- attempts to override system instructions (DAN, developer mode, persona hijacking)  
- **Prompt injection detection** \-- instruction injection, obfuscation techniques, payload splitting  
- **Harmful content detection** \-- requests for exploits, violence, regulated substances, hate speech, and 12+ additional harm categories

The system uses local LLM inference via Ollama and includes:

- Rule-based first-pass filtering (keyword matching, Shannon entropy checks)  
- Advanced deobfuscation preprocessing (Base64, ROT13, hex, Unicode escapes, leetspeak, zero-width characters, Braille, NATO phonetic, Morse code, and more)  
- Multi-turn conversation trajectory analysis (crescendo detection, topic drift, escalation rate)  
- Ensemble mode (primary \+ secondary model with conservative result combination)  
- Safety classifier integration (GPT-OSS-Safeguard for detailed categorization)  
- Few-shot examples curated from WildJailbreak and real-world attack data  
- Chain-of-thought reasoning embedded in structured JSON output

### System Boundary Diagram

![][image1]

### Human Review Points

- **Pre-release gate:** Human reviews evaluation report before approving model/config changes for production  
- **Threshold override:** When metrics fall into borderline ranges (e.g., accuracy between 85-90%), a human reviewer decides whether to proceed or iterate  
- **False positive triage:** Flagged false positives from the evaluation are reviewed by the security team to determine whether they represent genuine edge cases or classifier bugs

 

| 5 | Risk Framing |
| :---: | :---- |

 

| \# | Risk | Lifecycle Stage | Impact |
| :---- | :---- | :---- | :---- |
| 1 | **False negatives on safety classification** \-- the classifier fails to detect a jailbreak or harmful prompt | Validation / Deployment | Harmful content reaches end users; regulatory exposure |
| 2 | **False positives on benign prompts** \-- legitimate queries are blocked | Validation / Operation | User frustration; reduced utility of the AI assistant |
| 3 | **Model drift after updates** \-- swapping or fine-tuning the underlying LLM changes classification behavior without detection | Deployment / Operation | Silent degradation of safety controls |
| 4 | **Obfuscation bypass** \-- encoded or disguised attacks evade both rule-based and LLM-based detection | Validation | Entire categories of attacks go undetected |
| 5 | **Inconsistent classification** \-- the same prompt yields different results across runs or models | Validation | Unreliable safety guarantees; inability to set stable thresholds |
| 6 | **Evaluation hallucination** \-- the LLM judge itself produces incorrect evaluations (grades a wrong answer as correct) | Validation | False confidence in classifier performance |
| 7 | **Insufficient test coverage** \-- the evaluation dataset does not cover real-world attack diversity | Design / Validation | Metrics look good on paper but miss attack vectors seen in practice |

 

| 6 | Data Plan |
| :---: | :---- |

 

### Evaluation Dataset

The test dataset will be constructed from multiple sources to ensure coverage across attack categories:

| Source | Type | Approximate Size | Status |
| :---- | :---- | :---- | :---- |
| Existing test fixtures from analyze-prompt-intent | Single-turn prompts (27 files covering safe, jailbreak, injection, obfuscation, harmful, payload-split categories) | \~27 prompts | Real, already available |
| Existing conversation fixtures | Multi-turn conversations (15 JSONL files covering crescendo, escalation, hostile, safe patterns) | \~15 conversations | Real, already available |
| Expanded adversarial prompts | New prompts targeting edge cases identified during evaluation (subtle jailbreaks, borderline academic queries, false-positive-prone inputs) | \~50-75 additional prompts | Will be created; mix of manual curation and systematic generation |
| Ground truth labels | Manual labeling of expected classification for each prompt (jailbreak, injection, harmful, content\_flags, attack\_types) | Matches dataset size | Manual annotation |

### Data Schema

Each evaluation record will contain:

\`\`\`json  
{  
 "prompt\_id": "jailbreak\_dan\_001",  
 "category": "jailbreak",  
 "subcategory": "virtualization",  
 "prompt\_text": "You are DAN...",  
 "expected": {  
   "jailbreak": true,  
   "prompt\_injection": true,  
   "harmful\_content": true,  
   "min\_confidence": 0.85,  
   "expected\_attack\_types": \["Virtualization / Role-play"\],  
   "expected\_content\_flags": \["regulated\_substances"\]  
 },  
 "conversation\_history": null,  
 "metadata": {  
   "source": "WildJailbreak",  
   "difficulty": "medium"  
 }  
}  
\`\`\`

### Data Quality Risks

- **Label ambiguity:** Some prompts are genuinely borderline (e.g., security education requests). We will document these cases and assign confidence ranges rather than binary labels where appropriate.  
- **Coverage gaps:** The existing fixture set is weighted toward jailbreaks and obfuscation. We will deliberately add more benign prompts, subtle attacks, and multi-turn conversations to balance the dataset.  
- **No real production data:** All test data is simulated or curated. This is a known limitation. The evaluation framework itself, however, is designed to accept real data if it became available.

| 7 | Tool Stack |
| :---: | :---- |

### Open-Source Tool: Ollama with Model APIs (OpenAI-compatible)

**Role:** Ollama serves as the local LLM inference runtime for both the system under test and the LLM-as-a-Judge evaluator. It provides an OpenAI-compatible API at `http://localhost:11434/v1`.

**Why it is needed:**

- The entire analyze-prompt-intent system depends on local LLM inference through Ollama  
- The LLM-as-a-Judge evaluation itself requires calling a model to score classifier outputs  
- Multiple models (gpt-oss, qwen3, gpt-oss-safeguard) are used for ensemble and safety classification  
- No data leaves the local machine, which is critical for evaluating sensitive/harmful test prompts

**How it integrates:** Ollama is the inference backend for every LLM call in the pipeline. The commercial models running on Ollama (gpt-oss, qwen3) are commercially distributed models accessed through the Ollama platform.

### Commercial Tool: Evidently AI

**Role:** Monitoring, metric visualization, and reporting for evaluation results.

**Why it is needed:**

- Provides pre-built metric computation for classification tasks (accuracy, precision, recall, F1)  
- Generates visual HTML reports and dashboard views without requiring custom UI development  
- Supports drift detection to compare evaluation results across model versions  
- Produces exportable artifacts suitable for compliance review and audit

**How it integrates:** After each evaluation run, the pipeline formats results into Evidently-compatible datasets and generates classification performance reports, drift reports (when comparing across models or runs), and data quality summaries. These reports serve as the primary dashboard and evidence artifacts.

### Additional Open-Source Components

| Tool | Role |
| :---- | :---- |
| Python 3.12+ | Primary implementation language |
| Poetry | Dependency management (already used by analyze-prompt-intent) |
| Pytest | Unit and integration test framework for the evaluation pipeline itself |
| Pandas | Data manipulation for evaluation result aggregation |

 

 

| 8 | Implementation Plan |
| :---: | :---- |

 

### Component 1: Labeled Evaluation Dataset

Build a structured dataset of prompts with ground-truth labels covering all threat categories in the analyzer's taxonomy:

- Single-turn prompts: safe, jailbreak (5+ variants), prompt injection, obfuscation (Base64, ROT13, hex, leetspeak, Unicode), harmful content (across severity levels), adversarial suffixes, false-positive-prone inputs  
- Multi-turn conversations: crescendo attacks, payload splitting, topic drift, safe escalation, benign conversations  
- Each prompt annotated with expected classification output (boolean flags, confidence range, expected attack\_types, expected content\_flags)

### Component 2: Automated Evaluation Runner

A batch execution framework that:

- Iterates through the labeled dataset  
- Runs each prompt through analyze-prompt-intent (single model, ensemble mode, and with safety classifier)  
- Captures full JSON output for each run  
- Records execution metadata (model used, latency, timestamp)  
- Stores results in a structured format for downstream analysis

### Component 3: LLM-as-a-Judge Scoring Module

An evaluation module where a separate LLM call acts as a judge to assess classification quality:

- **Correctness scoring:** Does the classifier's boolean output (jailbreak/injection/harmful) match the ground truth?  
- **Reasoning quality:** Does the classifier's chain-of-thought reasoning cite specific evidence from the input? Is the reasoning logically sound?  
- **Confidence calibration:** Are high-confidence scores associated with correct classifications? Are borderline cases assigned appropriately lower confidence?  
- **Content flag completeness:** Did the classifier identify all expected harm categories?

The judge uses a separate prompt template that receives: (a) the original user prompt, (b) the expected classification, and (c) the classifier's actual output. It returns a structured quality score.

### Component 4: Metric Aggregation and Reporting

Compute standard classification metrics across the evaluation dataset:

- **Per-category accuracy:** Jailbreak detection rate, prompt injection detection rate, harmful content detection rate  
- **False positive rate:** Percentage of benign prompts incorrectly flagged  
- **False negative rate:** Percentage of malicious prompts missed  
- **Precision, recall, F1** for each threat dimension  
- **Confidence calibration curve:** Plotting confidence scores against actual correctness  
- **Obfuscation resilience:** Detection rates broken down by obfuscation technique  
- **Cross-model comparison:** How do results differ between primary model, ensemble mode, and with safety classifier enabled?

### Component 5: Evidently AI Dashboard and Reports

Generate Evidently classification performance reports including:

- Overall accuracy, precision, recall, and F1 visualization  
- Per-class performance breakdown  
- Confusion matrix visualization  
- Drift detection report comparing results across different model configurations or versions  
- Data quality report for the evaluation dataset itself

### Component 6: Release Gate Logic

A pass/fail decision framework based on evaluation results:

| Metric | Threshold | Action if Failed |
| :---- | :---- | :---- |
| Overall accuracy | \>= 90% | Block release |
| Jailbreak detection recall | \>= 90% | Block release |
| Harmful content detection recall | \>= 95% | Block release |
| False positive rate (benign prompts) | \<= 10% | Block release |
| Obfuscation detection rate | \>= 80% | Flag for review |
| Cross-model consistency (ensemble) | \>= 85% agreement | Flag for review |

 

| 9 | Validation Plan |
| :---: | :---- |

 

### How We Validate the Classifier

- **Automated test suite:** Run the full labeled dataset through the classifier and compute metrics against ground truth labels  
- **Cross-model comparison:** Run evaluations with different models (gpt-oss, qwen3, ensemble) and compare for consistency  
- **Obfuscation stress test:** Evaluate specifically against Base64, ROT13, hex, leetspeak, and Unicode-encoded prompts to measure deobfuscation effectiveness  
- **Multi-turn evaluation:** Test conversation trajectory analysis against labeled multi-turn attack sequences  
- **Boundary testing:** Evaluate prompts at the borderline between safe and harmful (e.g., academic chemistry questions, security education, roleplay requests) to measure calibration

### How We Validate the Judge

- **Manual review sample:** Randomly select 15-20 evaluation results from the LLM judge and manually verify the judge's scoring against the expected output. Document agreement rate.  
- **Judge consistency check:** Run the same evaluation twice and measure judge agreement with itself (self-consistency)  
- **Adversarial judge test:** Present the judge with intentionally incorrect classifier outputs to verify the judge does not rubber-stamp everything as correct

### How We Validate the Pipeline

- **Unit tests:** Test each pipeline component in isolation (dataset loader, result parser, metric calculator)  
- **Integration test:** End-to-end run from dataset input through to Evidently report generation  
- **Reproducibility check:** Run the full evaluation twice and compare metric outputs for stability

### Evidence Artifacts Produced

| Artifact | Format | Purpose |
| :---- | :---- | :---- |
| Per-prompt classification results | JSON | Raw data for analysis and audit |
| Metric summary report | JSON \+ Markdown | Overall performance snapshot |
| Evidently HTML report | HTML | Visual dashboard for stakeholder review |
| Confusion matrix | PNG/HTML | Visual classification performance |
| Release gate decision log | Markdown | Pass/fail record with justification |
| LLM judge scoring log | JSON | Evaluation quality evidence |
| Manual review sample | Markdown | Human validation of judge accuracy |

 

| 10 | Deliverables and Milestones |
| :---: | :---- |

| Milestone | Target Date | Owner | Deliverable |
| :---- | :---- | :---- | :---- |
| Dataset construction and labeling | April 16 | Aaron (prompts), Juan (labeling review) | Labeled evaluation dataset (JSON) |
| Evaluation runner implementation | April 18 | Aaron | Batch execution script with result capture |
| LLM-as-a-Judge module | April 20 | Aaron | Judge prompt template and scoring module |
| Metric aggregation module | April 21 | Aaron | Per-category metrics, confusion matrix, calibration |
| Evidently integration and dashboards | April 23 | Juan | HTML reports, drift detection setup |
| Release gate logic | April 23 | Juan | Pass/fail framework with documented thresholds |
| Pipeline validation (testing the tester) | April 24 | Aaron \+ Juan | Unit tests, manual review sample, judge consistency |
| Research documentation and risk analysis | April 20-25 | Juan | Written documentation of approach, limitations, related work |
| Final presentation preparation | April 25-27 | Juan (primary), Aaron (demo) | Slide deck, live demo plan, recorded video backup |
| All materials submitted | April 28, 4:00 PM | Both | GitHub repo, README, evidence folder, presentation |

 

 

| 11 | Role Allocation |
| :---: | :---- |

| Team Member | Primary Responsibilities |
| :---- | :---- |
| **Aaron Sweeney** | Technical implementation of the full evaluation pipeline: runner, judge module, metric aggregation, Evidently integration, release gates, unit/integration tests. Architecture decisions and code quality. Live demo during final presentation. |
| **Juan Martin Zambrano Lozano** | Research on LLM-as-a-Judge best practices and evaluation methodologies. Documentation of the approach, risk analysis, and limitations. Dataset labeling review and quality assurance. Primary creator of the final presentation slides and recorded video. |

Both team members will collaborate on:

- Defining evaluation criteria and thresholds  
- Reviewing evaluation results and identifying failure patterns  
- Preparing the final presentation narrative and defense

Both team members understand the full system architecture and can explain any component during the final presentation defense. 

 

|   | *Collaboration: daily async stand-up in a shared Teams channel; Thursday sync calls for design reviews; all code in a shared GitHub repo with PR reviews required for merges to main. Every member is expected to read and understand all four components before the final demo — the grader may ask any team member about any part of the system.* |
| :---- | :---- |

 

| 12 | Project Risks and Fallback Plan |
| :---: | :---- |

 

| Risk | Likelihood | Mitigation | Fallback |
| :---- | :---- | :---- | :---- |
| **LLM judge produces unreliable scores** | Medium | Use structured scoring rubric with few-shot examples; validate judge against manual review sample | Fall back to purely metric-based evaluation (accuracy, precision, recall) without reasoning quality assessment |
| **Ollama performance bottleneck** | Medium | Use smaller/faster models for the judge; batch prompts efficiently; run evaluations overnight if needed | Reduce dataset size to core categories; focus on single-model evaluation instead of full cross-model comparison |
| **Insufficient test coverage in time** | Low | Start with existing 42 fixtures; prioritize new prompts for under-covered categories | Ship with existing fixtures plus 20-30 targeted additions; document coverage gaps as known limitations |
| **Evidently integration complexity** | Low | Evidently has well-documented APIs for classification report generation; start integration early | Generate custom matplotlib charts and markdown reports as alternative visualization |
| **Model availability issues** | Low | Test with multiple Ollama models early; confirm all three models (gpt-oss, qwen3, gpt-oss-safeguard) are pullable and functional | Run evaluation with a single available model and document the limitation |
| **Scope creep** | Medium | Strictly follow the component list in Section 8; resist adding features beyond the defined pipeline | Cut cross-model comparison and focus on single-model evaluation with dashboarding |

 

|   | Stretch Goals Adversarial prompt generation: Use an LLM to automatically generate new adversarial prompts that target identified weaknesses in the classifier Temporal drift simulation: Run evaluations across multiple model versions to simulate how classifier performance changes over time CI/CD integration example: Package the evaluation pipeline as a GitHub Actions workflow that runs on every commit |
| :---- | :---- |

 

[image1]: <data:image/png;base64,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>