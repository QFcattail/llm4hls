# Fetched: https://xilinx.github.io/fpl26_optimization_contest/
- final_url: https://xilinx.github.io/fpl26_optimization_contest/
- status: 200
- chars: 7592

---

### Agentic FPGA Backend Optimization Competition

  * [Home](https://xilinx.github.io/fpl26_optimization_contest/index.html)
  * [Contest Details](https://xilinx.github.io/fpl26_optimization_contest/details.html)
  * [Optimization Example](https://xilinx.github.io/fpl26_optimization_contest/optimization_example.html)
  * [Eval. Environment](https://xilinx.github.io/fpl26_optimization_contest/runtime.html)
  * [Alpha Submission](https://xilinx.github.io/fpl26_optimization_contest/alpha_submission.html)
  * [Beta Submission](https://xilinx.github.io/fpl26_optimization_contest/beta_submission.html)
  * [Final Submission](https://xilinx.github.io/fpl26_optimization_contest/final_submission.html)
  * [Benchmarks](https://xilinx.github.io/fpl26_optimization_contest/benchmarks.html)
  * [Scoring Criteria](https://xilinx.github.io/fpl26_optimization_contest/score.html)
  * [FAQ](https://xilinx.github.io/fpl26_optimization_contest/FAQ.html)
  * [GitHub Repo](https://github.com/Xilinx/fpl26_optimization_contest)
  * [Contact](https://xilinx.github.io/fpl26_optimization_contest/contact.html)



_Sponsored by![](https://xilinx.github.io/fpl26_optimization_contest/AMD_E_Wh_RGB.jpg) ; contest hosted at the _[FPL'26 conference](https://2026.fpl.org/)_._

Hosted on [GitHub Pages](https://pages.github.com) using the Dinky theme

# Agentic FPGA Backend Optimization Competition @ [FPL'26](https://2026.fpl.org/)

## The Challenge

Given a fully placed and routed design checkpoint (](https://xilinx.github.io/fpl26_optimization_contest/DCP), create a new DCP that improves its maximum clock frequency (](https://xilinx.github.io/fpl26_optimization_contest/Fmax) as much as possible while maintaining logical equivalence and staying fully placed and routed.

## Introduction

Achieving FPGA timing closure can often be challenging and time-consuming. Long place and route compile times, coupled with the frustration of missing timing, often by narrow margins, demands new automated approaches. To address this bottleneck, we present the Agentic FPGA Backend Optimization Competition at FPL 2026. This contest leverages Agentic AI, open-source CAD frameworks (](https://xilinx.github.io/fpl26_optimization_contest/[RapidWright](http:/rapidwright.io)), and commercial tools (](https://xilinx.github.io/fpl26_optimization_contest/[AMD Vivado™](https:/www.amd.com/en/products/software/adaptive-socs-and-fpgas/vivado.html)) to democratize implementation improvements and timing closure techniques previously only possible by the most experienced engineers.

Your browser does not support the video tag. 

Contest participants can utilize Large Language Models (](https://xilinx.github.io/fpl26_optimization_contest/LLMs) and Model Context Protocol (](https://xilinx.github.io/fpl26_optimization_contest/MCP) servers to architect autonomous agents capable of analyzing existing placed-and-routed designs, formulating optimization strategies, and applying ECO-like modifications to iteratively converge onto improved implementation results.

Teams will differentiate their solutions in three key areas:

  1. New and Customized Optimizations: Developing specific targeted interventions, such as merging LUTs in critical paths or replicating source cells on high-fanout nets.
  2. Strategic Analysis & Batching: Creating analysis heuristics that maximize the application of beneficial optimizations within a fixed time budget.
  3. Prompt Engineering & Context management: Developing techniques to optimize prompt efficacy, efficient problem formulations for LLMs, and mitigate context window limitations.



The competition objective is to create an automated agentic flow that consumes a placed and routed Vivado Design Checkpoint (](https://xilinx.github.io/fpl26_optimization_contest/DCP) and produces a functionally equivalent DCP with improved Fmax. Finalists will be announced at FPL 2026 and awarded cash prizes, with additional incentives provided for teams that open-source their submissions to the community.

To this end, the biggest component of the contest score will be Fmax improvement.

A high-level flow : [![image](https://xilinx.github.io/fpl26_optimization_contest/fpl26-contest-overview-flow.jpg)](https://xilinx.github.io/fpl26_optimization_contest/fpl26-contest-overview-flow.jpg) More information can be found in [Contest Details](https://xilinx.github.io/fpl26_optimization_contest/details.html).

## Important Dates (](https://xilinx.github.io/fpl26_optimization_contest/Tentative)

Date |   
---|---  
23 February 2026 | Contest Announced  
~~23 March 2026~~  
**EXTENDED 3 April 2026** | Registration Deadline (](https://xilinx.github.io/fpl26_optimization_contest/mandatory, see below)  
5 May 2026 | Alpha Submission (](https://xilinx.github.io/fpl26_optimization_contest/[details](https:/xilinx.github.io/fpl26_optimization_contest/alpha_submission.html))  
13 July 2026 | Beta Submission (](https://xilinx.github.io/fpl26_optimization_contest/[details](https:/xilinx.github.io/fpl26_optimization_contest/beta_submission.html))  
10 August 2026 | Final Submission (](https://xilinx.github.io/fpl26_optimization_contest/[details](https:/xilinx.github.io/fpl26_optimization_contest/final_submission.html))  
6-10 September 2026 | Prizes awarded to top 5 teams at [FPL 2026 conference](https://2026.fpl.org/)  
  
Deadlines refer to Anywhere On Earth.

## Prizes

Prizes will be awarded to up to 5 finalists:

Rank | Prize (](https://xilinx.github.io/fpl26_optimization_contest/Euro)  
---|---  
1st | **€3000**  
2nd | **€2000**  
3rd | **€1000**  
4th & 5th | **€500**  
  
Prize amounts subject to change.

_**Note 1:**_ _50% of the prize money is conditional on the winning entry being made open source under a permissive license (](https://xilinx.github.io/fpl26_optimization_contest/BSD, MIT, Apache) within 30 days of award announcement. This is to encourage participants to help the FPGA community and ecosystem grow faster._  
_**Note 2:**_ _Applicable taxes may be assessed on and deducted from award payments, subject to U.S. and/or local government policies._

## Registration

Contest registration is mandatory to be eligible for alpha submission and final prizes. To register, please [send an email](mailto:chris.lavin@amd.com) with the following information:

  * Subject: `FPL26 Contest Registration`
  * Body:
        
        Team name: <TEAM NAME>
        Team members and affiliation:
          <NAME> (](https://xilinx.github.io/fpl26_optimization_contest/<AFFILIATION>)
          <NAME> (](https://xilinx.github.io/fpl26_optimization_contest/<AFFILIATION>)
        Advising Professor (](https://xilinx.github.io/fpl26_optimization_contest/if applicable): <NAME> (](https://xilinx.github.io/fpl26_optimization_contest/<AFFILIATION>)
        Single corresponding email: <NAME@AFFILIATION.COM>
        




Team size is limited to 6 members (](https://xilinx.github.io/fpl26_optimization_contest/not including advisor(s)).

For development on local hardware, a Vivado license will likely be needed, however, eligible teams from academia can ask their advising professor to apply for a donation of a Vivado license from the AMD University Program. The advisor can access the donation request form [here](https://www.amd.com/en/corporate/university-program/donation-program.html). Please ask your advisor to request the number of Vivado licenses you need and add a reference to the FPL contest in the comments section of the donation form.

## Disclaimer

The organizers reserve the rights to revise or modify any aspect of this contest at any time.
