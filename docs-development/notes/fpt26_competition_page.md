Design Competition
    * Call for Special Sessions
    * Call for Tutorials
    * Call for Workshops
    * Call for Artifact Form
    * Call for PhD Forum
  * Program
  * Committees
    * Organizing Committee
    * Technical Program Committee
    * Steering Committee
  * Attend
    * Venue
    * Visa

  * __ Search Toggle search interface
  * __ Menu Toggle extended navigation

# FPT'26 Design Competition

**For a promotional flyer of Call for Design Competition, please click here.**

**Unleash the Future of FPGA-Accelerated AI**

**Sponsored By**

## Competition Overview: Where AI Meets Hardware Innovation

The field of artificial intelligence is currently experiencing a paradigm shift, characterized by the exponential growth in model complexity and a corresponding demand for efficient computing platforms. Field-Programmable Gate Arrays (FPGAs), with their inherent advantages in parallelism, low latency, energy efficiency, and reconfigurability, have emerged as a promising platform for accelerating modern AI workloads. However, fully realizing the potential of FPGAs requires significant advancements in both **AI-driven design automation** and **hardware-aware design optimization**.

The FPT'26 Design Competition invites global teams to address these challenges through two distinct yet complementary tracks that represent cutting-edge directions in intelligent computing:

  * **Track A (LLM4HLS)** : This track focuses on the development of an _autonomous AI agent_ capable of _generating, debugging, and optimizing High-Level Synthesis (HLS) code_ through an iterative process. The agent must operate within strict tool invocation budgets, with the objective of achieving functional correctness and high-quality Performance, Power, and Area (PPA) metrics. This track explores the future of hardware design, where AI systems play an active role in the engineering process.
  * **Track B (Attention Acceleration)** : This track addresses the FPGA acceleration of attention mechanisms, a core component of modern Transformer architectures. Participants are required to design efficient architecture aligned with the Llama3-8B model specification, leveraging customized dataflow, fine-grained parallelism, and hardware-aware optimization techniques to achieve state-of-the-art deployment efficiency.

This competition welcomes participants from diverse backgrounds, including but not limited to hardware architecture, machine learning, compiler design, and electronic design automation (EDA). It provides an opportunity to showcase innovative solutions that may shape the future of computing.

## Eligibility & Registration

  * Open worldwide to teams from universities and research institutes. Industry-academia collaboration is encouraged.
  * Each team may consist of 1 to 4 student participants and up to 2 advisors. Each individual may participate in only one team. Cross-team participation is not allowed. To ensure fair competition, this year’s design competition is open only to students.
  * Interdisciplinary collaboration is strongly encouraged, as the challenges span multiple domains including computer architecture, EDA, FPGA design, systems, and machine learning.
  * Registration is via the China National Undergraduate Embedded Chip and System Design Competition(www.fpgachina.cn). Detailed registration procedures could be referred to https://docs.qq.com/doc/DYUhVVUdpcHpSV0F0

## Rules & Policies

  * Original work only; new contributions required.
  * Only AMD-supported FPGA and AIE platforms are accepted.
  * Any AMD or open-source toolchains allowed.
  * Confidential details may be withheld from public release but must be shared with judges.
  * All participants must follow FPT’s professional conduct policy.
  * Finalists should attend in person for demo; remote demos are not eligible for awards.

**Important Dates (all 23:59 AoE)**

**Phase** |  **Deadline** |  **Description**  
---|---|---  
Registration Deadline |  July 7, 2026 |  Team registration  
Submission Deadline |  August 7, 2026 |  Technical material submission  
Shortlist Announcement |  August 21, 2026 |  Finalist teams announced  
  
## Tracks Introduction

The 2026 competition features two distinct but complementary tracks:

**Track A: Budgeted End-to-End LLM4HLS Agent**

This track requires participants to develop an autonomous agent capable of addressing a range of HLS tasks under constrained tool invocation budgets. Each task is provided as a problem statement that may contain at least one of several initial conditions:

  * A functionally correct but unoptimized baseline C/C++ implementation.
  * An HLS design that fails compilation or synthesis.
  * An HLS design that compiles successfully but fails C simulation, co-simulation, or hidden functional tests.
  * An HLS design that exhibits structural issues such as deadlock, invalid streaming behavior, or severe resource inefficiency.
  * Other problems related to HLS compilation.

The agent must iteratively generate, repair, or optimize candidate HLS code by calling the provided evaluation interfaces. A successful submission should demonstrate the following complete workflow:

  * Interpretation of the task specification and initial code.
  * Generation or modification of HLS C/C++ code (including pragmas).
  * Invocation of tool feedback interfaces.
  * Parsing of logs and reports for issue diagnosis.
  * Prioritization of correctness issue resolution before PPA optimization.
  * Termination within the assigned budget constraints.

Each task will include the following artifacts:

  * **Source files:** Baseline C/C++, with several problems indicated as above.
  * **Testbench:** Public correctness tests, building scripts (e.g. Makefile).
  * **Specification:** Interface contract, data types, numerical tolerance, and design constraints.
  * **Target constraints:** FPGA platform, HLS tool version, clock target, and optional resource limits.
  * **Budget configuration:** Maximum iterations allowed calls to csim, cosim, and synth, or an equivalent unified credit budget.

Submitted entries will be evaluated based on the following primary dimensions: **correctness** , **PPA metrics** , and**problem difficulties.**

**Track B: FPGA Based Attention Acceleration**

The attention module represents a fundamental component of modern Large Language Models (LLMs). However, the efficient deployment of attention mechanisms on FPGA platforms remains a significant research challenge. This track focuses on the Llama3-8B or models with consistent parameters. Participants are required to implement an attention accelerator on an FPGA platform that supports bf16 data type.

**Hardware resource constraints** (participants must select one configuration):

  * With AI cores: No more than 64 AI Engines, DSPs/LUTs/FFs as fewer as possible.
  * Without AI cores: DSPs/LUTs/FFs as fewer as possible.

Submitted entries will be evaluated based on the following primary dimensions: **performance** , **hardware architecture optimizations** , and**scalability.**

## Submission Requirement

  * Project Description: Participants are required to submit a technical paper electronically in PDF format, following the IEEE conference double-column format. The main content should not exceed **two pages** , with optional unlimited appendices as additional materials.
  * Demonstration Video (max 5 min): must show project running on target platform with clear explanation.
  * For recommended submission guidelines for Track A and Track B, please visit https://github.com/FPT26/Design-Competition-Submission-Guidelines.

## Judging Criteria

  * Technical merit (40%)
  * Innovation (20%)
  * Practical impact (20%)
  * Clarity of presentation and reproduction (20%)

## Final Stage

  * Finalists are required to register for the conference (**Full Registration**).
  * Finalists must present their work in person at FPT 2026 to qualify for awards.
  * Finalist teams will have the option to include a short 2-page paper in the official IEEE FPT 2026 proceedings, summarizing their projects. This is optional and intended to give visibility to the work within the archival record of the conference.

**Awards**

**Award** |  **Selection Criterion**  
---|---  
1st/2nd/3rd Place |  Certificate, FPT proceedings invitation  
Excellence Award |  Certificate  
  
## Contact and Information

As for the general enquiry, please contact email (erie@seu.edu.cn). 

Submission portal, and frequently asked questions will be announced in due course.

### Contact Information

icfpt2026@gmail.com

### Disclaimer

Policy 225.0. This website is a component of a program managed by University of Arkansas faculty, students or staff but is otherwise independent of the University of Arkansas.

Privacy Policy

Accessibility Statement

---

> 来源：https://fpt2026.uark.edu/fpt26-design-competition/
> 提取：2026-07-11，从 `contest/FPT26_Competition_Page.html` 转为 Markdown