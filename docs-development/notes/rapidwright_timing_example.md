# Fetched: https://www.rapidwright.io/docs/ReportTimingExample.html
- final_url: https://www.rapidwright.io/docs/ReportTimingExample.html
- status: 200
- chars: 22320

---

[![Logo](https://www.rapidwright.io/docs/_static/rwlogo_xsm_black.png)](http://rapidwright.io)  
[ RapidWright Docs ](https://www.rapidwright.io/docs/index.html)

2026.1.0 

  * [Introduction](https://www.rapidwright.io/docs/Introduction.html)
  * [Getting Started](https://www.rapidwright.io/docs/Getting_Started.html)
  * [FPGA Architecture Basics](https://www.rapidwright.io/docs/FPGA_Architecture.html)
  * [Xilinx Architecture Terminology](https://www.rapidwright.io/docs/Xilinx_Architecture.html)
  * [RapidWright Overview](https://www.rapidwright.io/docs/RapidWright_Overview.html)
  * [Design Checkpoints](https://www.rapidwright.io/docs/Design_Checkpoints.html)
  * [Implementation Basics](https://www.rapidwright.io/docs/Implementation_Basics.html)
  * [Merging Designs](https://www.rapidwright.io/docs/Merge_Designs.html)
  * [Bitstream Manipulation](https://www.rapidwright.io/docs/Bitstream_Manipulation.html)
  * [FPGA Interchange Format](https://www.rapidwright.io/docs/FPGA_Interchange_Format.html)
  * [RapidWright Publications](https://www.rapidwright.io/docs/Papers.html)
  * [A Pre-implemented Module Flow](https://www.rapidwright.io/docs/PreImplemented_Module_Flow.html)
  * [RapidWright Tutorials](https://www.rapidwright.io/docs/Tutorials.html)
    * [RWRoute Timing-driven Routing](https://www.rapidwright.io/docs/RWRoute_timing_driven_routing.html)
    * [RWRoute Wirelength-driven Routing](https://www.rapidwright.io/docs/RWRoute_wirelength_driven_routing.html)
    * [RWRoute Partial Routing](https://www.rapidwright.io/docs/RWRoute_partial_routing.html)
    * RapidWright Report Timing Example
      * Background
      * Steps to Run
      * Example Output
      * Compare with Vivado
    * [Reuse Timing-closed Logic As A Shell](https://www.rapidwright.io/docs/ReusingTimingClosedLogicAsAShell.html)
    * [Use DREAMPlaceFPGA to Place a Netlist via FPGA Interchange Format](https://www.rapidwright.io/docs/Use_DREAMPlaceFPGA_via_FPGA_Interchange_Format.html)
    * [Polynomial Generator: Placed and Routed Circuits in Seconds](https://www.rapidwright.io/docs/PolynomialGenerator.html)
    * [Inserting and Routing a Debug Core As An ECO](https://www.rapidwright.io/docs/ECO_Insert_Route_Debug.html)
    * [Create Placed and Routed DCP to Cross SLR](https://www.rapidwright.io/docs/SLR_Crosser_DCP_Creator_Tutorial.html)
    * [Build an IP Integrator Design with Pre-Implemented Blocks](https://www.rapidwright.io/docs/IPI_PreImpl_Tutorial.html)
    * [RapidWright PipelineGenerator Example](https://www.rapidwright.io/docs/PipelineGeneratorExample.html)
    * [RapidWright PipelineGeneratorWithRouting Example](https://www.rapidwright.io/docs/PipelineGeneratorExampleWithRouting.html)
    * [Pre-implemented Modules - Part I](https://www.rapidwright.io/docs/PreImplemented_Modules_Part_I.html)
    * [Pre-implemented Modules - Part II](https://www.rapidwright.io/docs/PreImplemented_Modules_Part_II.html)
    * [Create and Use an SLR Bridge](https://www.rapidwright.io/docs/Create_and_Use_an_SLR_Bridge.html)
    * [RapidWright FPGA 2019 Deep Dive Tutorial](https://www.rapidwright.io/docs/FPGA19_Workshop.html)
    * [RapidWright FCCM 2019 Workshop](https://www.rapidwright.io/docs/FCCM19_Workshop.html)
    * [RapidWright FPL 2019 Tutorial](https://www.rapidwright.io/docs/FPL19_Tutorial.html)
    * [RapidWright ICCAD 2023 Hands-on Tutorial](https://www.rapidwright.io/docs/ICCAD23_Tutorial.html)
  * [Tech Articles](https://www.rapidwright.io/docs/Tech_Articles.html)
  * [Frequently Asked Questions](https://www.rapidwright.io/docs/FAQ.html)
  * [Glossary](https://www.rapidwright.io/docs/Glossary.html)



  
  
[Download PDF  
![](https://www.rapidwright.io/docs/_static/pdf.svg)](https://www.rapidwright.io/docs/RapidWright.pdf)   
  
  
[Javadoc API Reference  
![](https://www.rapidwright.io/docs/_static/javadoc.svg)](https://www.rapidwright.io/javadoc/index.html)

__[RapidWright Docs](https://www.rapidwright.io/docs/index.html)

  * [Docs](https://www.rapidwright.io/docs/index.html) »
  * [RapidWright Tutorials](https://www.rapidwright.io/docs/Tutorials.html) »
  * RapidWright Report Timing Example
  * [ View page source](https://www.rapidwright.io/docs/_sources/ReportTimingExample.rst.txt)



* * *

# RapidWright Report Timing Example¶

Reports the critical path within an example design (](https://www.rapidwright.io/docs/e.g. “microblaze4.dcp”).

## Background¶

Please see our FPT‘19 paper, [`"An Open-source Lightweight Timing Model for RapidWright"`](https://www.rapidwright.io/docs/_downloads/cf26778447e5d2f4a71de84d0b83d98e/FPT19-TimingModel.pdf) (](https://www.rapidwright.io/docs/[`Presentation`](https:/www.rapidwright.io/docs/_downloads/984b913379f4fcd771f876e83ce254df/FPT19-TimingModel-Presentation.pdf)) for background details on our RapidWright Timing Model.

## Steps to Run¶

  1. Download the example [`microblaze4.dcp`](https://www.rapidwright.io/docs/_downloads/5d2e79149a23766ae4e3c8958327c26c/microblaze4.dcp) design:



    
    
    wget http://www.rapidwright.io/docs/_downloads/microblaze4.dcp
    

  2. Invoke RWRoute via gradle (](https://www.rapidwright.io/docs/this will ensure code is compiled before running):



    
    
    rapidwright ReportTimingExample microblaze4.dcp
    

The source code for `ReportTimingExample.java` is provided below for easy reference:

> 
>     public static void main(](https://www.rapidwright.io/docs/String[] args) {
>         if(](https://www.rapidwright.io/docs/args.length != 1) {
>             System.out.println(](https://www.rapidwright.io/docs/"USAGE: <dcp_file_name>");
>             return;
>         }
>         CodePerfTracker t = new CodePerfTracker(](https://www.rapidwright.io/docs/"Report Timing Example");
>         t.useGCToTrackMemory(](https://www.rapidwright.io/docs/true);
>     
>         // Read in an example placed and routed DCP
>         t.start(](https://www.rapidwright.io/docs/"Read DCP");
>         Design design = Design.readCheckpoint(](https://www.rapidwright.io/docs/args[0], CodePerfTracker.SILENT);
>     
>         // Instantiate and populate the timing manager for the design
>         t.stop().start(](https://www.rapidwright.io/docs/"Create TimingManager");
>         TimingManager tim = new TimingManager(](https://www.rapidwright.io/docs/design);
>     
>         // Get and print out worst data path delay in design
>         t.stop().start(](https://www.rapidwright.io/docs/"Get Max Delay");
>         GraphPath<TimingVertex, TimingEdge> criticalPath = tim.getTimingGraph().getMaxDelayPath();
>     
>         // Print runtime summary
>         t.stop().printSummary();
>         System.out.println(](https://www.rapidwright.io/docs/"\nCritical path: "+ ((int)criticalPath.getWeight())+ " ps");
>         System.out.println(](https://www.rapidwright.io/docs/"\nPath details:");
>         System.out.println(](https://www.rapidwright.io/docs/criticalPath.toString().replace(](https://www.rapidwright.io/docs/",", ",\n")+"\n");
>     }
>     

## Example Output¶

Please refer to the timing library [Javadoc](http://www.rapidwright.io/javadoc/index.html) and code for more implementation details. The Java source code for the timing library is located in: [RapidWright/src/com/xilinx/rapidwright/timing/](https://github.com/Xilinx/RapidWright/tree/master/src/com/xilinx/rapidwright/timing).

Example output using the `microblaze4.dcp` design is included below:
    
    
    ==============================================================================
        ==                          Report Timing Example                           ==
        ==============================================================================
                            Read DCP:     6.275s    436.922MBs
                Create TimingManager:     1.838s     19.600MBs
                       Get Max Delay:     0.087s      0.213MBs
        ------------------------------------------------------------------------------
                             *Total*:     8.200s    456.734MBs
    
        Critical path: 1921 ps
    
        Path details:
        [superSource -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Operand_Select_I/EX_Op2_reg[31]/Q,
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Operand_Select_I/EX_Op2_reg[31]/Q -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Using_FPGA.ALL_Bits[31].ALU_Bit_I1/Not_Last_Bit.I_ALU_LUT_V5/Using_FPGA.Native/LUT6/I0,
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Using_FPGA.ALL_Bits[31].ALU_Bit_I1/Not_Last_Bit.I_ALU_LUT_V5/Using_FPGA.Native/LUT6/I0 -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Using_FPGA.ALL_Bits[31].ALU_Bit_I1/Not_Last_Bit.I_ALU_LUT_V5/Using_FPGA.Native/LUT6/O,
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Using_FPGA.ALL_Bits[31].ALU_Bit_I1/Not_Last_Bit.I_ALU_LUT_V5/Using_FPGA.Native/LUT6/O -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Use_Carry_Decoding.CarryIn_MUXCY/Using_FPGA.Native_CARRY4_CARRY8/S[1],
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Use_Carry_Decoding.CarryIn_MUXCY/Using_FPGA.Native_CARRY4_CARRY8/S[1] -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Use_Carry_Decoding.CarryIn_MUXCY/Using_FPGA.Native_CARRY4_CARRY8/CO[7],
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Use_Carry_Decoding.CarryIn_MUXCY/Using_FPGA.Native_CARRY4_CARRY8/CO[7] -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Using_FPGA.ALL_Bits[24].ALU_Bit_I1/Not_Last_Bit.MUXCY_XOR_I/Using_FPGA.Native_I1_CARRY4_CARRY8/CI,
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Using_FPGA.ALL_Bits[24].ALU_Bit_I1/Not_Last_Bit.MUXCY_XOR_I/Using_FPGA.Native_I1_CARRY4_CARRY8/CI -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Using_FPGA.ALL_Bits[24].ALU_Bit_I1/Not_Last_Bit.MUXCY_XOR_I/Using_FPGA.Native_I1_CARRY4_CARRY8/O[2],
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/ALU_I/Using_FPGA.ALL_Bits[24].ALU_Bit_I1/Not_Last_Bit.MUXCY_XOR_I/Using_FPGA.Native_I1_CARRY4_CARRY8/O[2] -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/Using_FPGA.Native_i_1__73/I0,
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/Using_FPGA.Native_i_1__73/I0 -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/Using_FPGA.Native_i_1__73/O,
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/Using_FPGA.Native_i_1__73/O -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/PreFetch_Buffer_I1/Instruction_Prefetch_Mux[33].Gen_Instr_DFF/Using_FPGA.Native_i_1__33/I0,
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/PreFetch_Buffer_I1/Instruction_Prefetch_Mux[33].Gen_Instr_DFF/Using_FPGA.Native_i_1__33/I0 -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/PreFetch_Buffer_I1/Instruction_Prefetch_Mux[33].Gen_Instr_DFF/Using_FPGA.Native_i_1__33/O,
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/PreFetch_Buffer_I1/Instruction_Prefetch_Mux[33].Gen_Instr_DFF/Using_FPGA.Native_i_1__33/O -> microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Operand_Select_I/EX_Branch_CMP_Op1_reg[22]/D,
         microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Operand_Select_I/EX_Branch_CMP_Op1_reg[22]/D -> superSink]
    

The `GraphPath<TimingVertex, TimingEdge>` object contains a path/set of edges. From each `TimingEdge` you can access the net delay and/or the logic delay values for more detail.

This example was designed to illustrate the default way to use the timing library to report the critical path and its associated data path delay.

## Compare with Vivado¶

To compare the output of the RapidWright timing model to Vivado, run the following at the prompt:
    
    
    vivado -mode tcl microblaze4.dcp
    

and then run the following command at the Tcl prompt:
    
    
    report_timing
    

In Vivado 2020.1, the timing report shows a data path delay of 1.846 ns (](https://www.rapidwright.io/docs/1846 ps). Which has an error of 30 ps or ~1.6%. The full Vivado timing report is shown below:
    
    
    -----------------------------------------------------------------------------------------
    | Tool Version      : Vivado v.2020.1 (](https://www.rapidwright.io/docs/lin64) Build 2902540 Wed May 27 19:54:35 MDT 2020
    | Date              : Mon Nov  8 22:17:03 2021
    | Host              : yun-Latitude-3470 running 64-bit Ubuntu 16.04.7 LTS
    | Command           : report_timing
    | Design            : design_1
    | Device            : xcvu3p-ffvc1517
    | Speed File        : -2  PRODUCTION 1.27 02-28-2020
    | Temperature Grade : E
    -----------------------------------------------------------------------------------------
    
    Timing Report
    
    Slack (](https://www.rapidwright.io/docs/MET) :             0.051ns  (](https://www.rapidwright.io/docs/required time - arrival time)
    Source:                 microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Operand_Select_I/EX_Branch_CMP_Op1_reg[8]/C
                                (](https://www.rapidwright.io/docs/rising edge-triggered cell FDRE clocked by TS_clk  {rise@0.000ns fall@1.000ns period=2.000ns})
    Destination:            microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Use_Debug_Logic.Master_Core.Debug_Perf/single_step_count_reg[0]/CE
                                (](https://www.rapidwright.io/docs/rising edge-triggered cell FDRE clocked by TS_clk  {rise@0.000ns fall@1.000ns period=2.000ns})
    Path Group:             TS_clk
    Path Type:              Setup (](https://www.rapidwright.io/docs/Max at Slow Process Corner)
    Requirement:            2.000ns  (](https://www.rapidwright.io/docs/TS_clk rise@2.000ns - TS_clk rise@0.000ns)
    Data Path Delay:        1.846ns  (](https://www.rapidwright.io/docs/logic 0.730ns (39.545%)  route 1.116ns (](https://www.rapidwright.io/docs/60.455%))
    Logic Levels:           7  (](https://www.rapidwright.io/docs/CARRY8=4 LUT2=1 LUT4=1 LUT6=1)
    Clock Path Skew:        -0.007ns (](https://www.rapidwright.io/docs/DCD - SCD + CPR)
    Destination Clock Delay (](https://www.rapidwright.io/docs/DCD):    0.021ns = (](https://www.rapidwright.io/docs/2.021 - 2.000 )
    Source Clock Delay      (](https://www.rapidwright.io/docs/SCD):    0.028ns
    Clock Pessimism Removal (](https://www.rapidwright.io/docs/CPR):    0.000ns
    Clock Uncertainty:      0.035ns  (](https://www.rapidwright.io/docs/(TSJ^2 + TIJ^2)^1/2 + DJ) / 2 + PE
    Total System Jitter     (](https://www.rapidwright.io/docs/TSJ):    0.071ns
    Total Input Jitter      (](https://www.rapidwright.io/docs/TIJ):    0.000ns
    Discrete Jitter          (](https://www.rapidwright.io/docs/DJ):    0.000ns
    Phase Error              (](https://www.rapidwright.io/docs/PE):    0.000ns
    
    Location             Delay type                Incr(](https://www.rapidwright.io/docs/ns)  Path(](https://www.rapidwright.io/docs/ns)    Netlist Resource(](https://www.rapidwright.io/docs/s)
    -------------------------------------------------------------------    -------------------
                             (](https://www.rapidwright.io/docs/clock TS_clk rise edge)     0.000     0.000 r
                                                          0.000     0.000 r  Clk_0 (](https://www.rapidwright.io/docs/IN)
                             net (](https://www.rapidwright.io/docs/fo=835, unset)          0.028     0.028    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Operand_Select_I/Clk
    SLICE_X75Y108        FDRE                                         r  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Operand_Select_I/EX_Branch_CMP_Op1_reg[8]/C
    -------------------------------------------------------------------    -------------------
    SLICE_X75Y108        FDRE (](https://www.rapidwright.io/docs/Prop_DFF2_SLICEL_C_Q)
                                                          0.081     0.109 f  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Operand_Select_I/EX_Branch_CMP_Op1_reg[8]/Q
                             net (](https://www.rapidwright.io/docs/fo=1, routed)           0.300     0.409    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Zero_Detect_I/Using_FPGA.Native_0[21]
    SLICE_X75Y108        LUT6 (](https://www.rapidwright.io/docs/Prop_C6LUT_SLICEL_I2_O)
                                                          0.088     0.497 r  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Zero_Detect_I/S0_inferred__3/i_/O
                             net (](https://www.rapidwright.io/docs/fo=1, routed)           0.010     0.507    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Zero_Detect_I/Part_Of_Zero_Carry_Start/lopt_5
    SLICE_X75Y108        CARRY8 (](https://www.rapidwright.io/docs/Prop_CARRY8_SLICEL_S[2]_CO[7])
                                                          0.155     0.662 f  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Data_Flow_I/Zero_Detect_I/Part_Of_Zero_Carry_Start/Using_FPGA.Native_CARRY4_CARRY8/CO[7]
                             net (](https://www.rapidwright.io/docs/fo=1, routed)           0.026     0.688    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/jump_logic_I1/MUXCY_JUMP_CARRY2/jump_carry1
    SLICE_X75Y109        CARRY8 (](https://www.rapidwright.io/docs/Prop_CARRY8_SLICEL_CI_CO[1])
                                                          0.042     0.730 f  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/jump_logic_I1/MUXCY_JUMP_CARRY2/Using_FPGA.Native_CARRY4_CARRY8/CO[1]
                             net (](https://www.rapidwright.io/docs/fo=1, routed)           0.117     0.847    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/jump_logic_I1/MUXCY_JUMP_CARRY3/ex_jump_wanted
    SLICE_X74Y109        LUT4 (](https://www.rapidwright.io/docs/Prop_D6LUT_SLICEM_I0_O)
                                                          0.051     0.898 r  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/jump_logic_I1/MUXCY_JUMP_CARRY3/Using_FPGA.Native_i_1__100/O
                             net (](https://www.rapidwright.io/docs/fo=1, routed)           0.025     0.923    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/mem_wait_on_ready_N_carry_or/MUXCY_I/lopt_9
    SLICE_X74Y109        CARRY8 (](https://www.rapidwright.io/docs/Prop_CARRY8_SLICEM_S[3]_CO[7])
                                                          0.163     1.086 r  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/mem_wait_on_ready_N_carry_or/MUXCY_I/Using_FPGA.Native_CARRY4_CARRY8/CO[7]
                             net (](https://www.rapidwright.io/docs/fo=1, routed)           0.026     1.112    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/Use_MuxCy[7].OF_Piperun_Stage/MUXCY_I/of_PipeRun_carry_5
    SLICE_X74Y110        CARRY8 (](https://www.rapidwright.io/docs/Prop_CARRY8_SLICEM_CI_CO[4])
                                                          0.099     1.211 r  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Decode_I/Use_MuxCy[7].OF_Piperun_Stage/MUXCY_I/Using_FPGA.Native_CARRY4_CARRY8/CO[4]
                             net (](https://www.rapidwright.io/docs/fo=324, routed)         0.472     1.683    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Use_Debug_Logic.Master_Core.Debug_Perf/of_piperun_for_ce
    SLICE_X80Y99         LUT2 (](https://www.rapidwright.io/docs/Prop_F6LUT_SLICEM_I1_O)
                                                          0.051     1.734 r  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Use_Debug_Logic.Master_Core.Debug_Perf/single_step_count[0]_i_1/O
                             net (](https://www.rapidwright.io/docs/fo=2, routed)           0.140     1.874    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Use_Debug_Logic.Master_Core.Debug_Perf/single_step_count[0]_i_1_n_0
    SLICE_X80Y99         FDRE                                         r  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Use_Debug_Logic.Master_Core.Debug_Perf/single_step_count_reg[0]/CE
    -------------------------------------------------------------------    -------------------
    
                             (](https://www.rapidwright.io/docs/clock TS_clk rise edge)     2.000     2.000 r
                                                          0.000     2.000 r  Clk_0 (](https://www.rapidwright.io/docs/IN)
                             net (](https://www.rapidwright.io/docs/fo=835, unset)          0.021     2.021    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Use_Debug_Logic.Master_Core.Debug_Perf/Clk
    SLICE_X80Y99         FDRE                                         r  microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Use_Debug_Logic.Master_Core.Debug_Perf/single_step_count_reg[0]/C
                             clock pessimism              0.000     2.021
                             clock uncertainty           -0.035     1.986
    SLICE_X80Y99         FDRE (](https://www.rapidwright.io/docs/Setup_HFF2_SLICEM_C_CE)
                                                         -0.061     1.925    microblaze_0/U0/MicroBlaze_Core_I/Performance.Core/Use_Debug_Logic.Master_Core.Debug_Perf/single_step_count_reg[0]
    -------------------------------------------------------------------
                             required time                          1.925
                             arrival time                          -1.874
    -------------------------------------------------------------------
                             slack                                  0.051
    

[Next ](https://www.rapidwright.io/docs/ReusingTimingClosedLogicAsAShell.html "Reuse Timing-closed Logic As A Shell") [ Previous](https://www.rapidwright.io/docs/RWRoute_partial_routing.html "RWRoute Partial Routing")

* * *

(](https://www.rapidwright.io/docs/C) Copyright 2018-2026, Advanced Micro Devices, Inc. 

Built with [Sphinx](http://sphinx-doc.org/) using a [theme](https://github.com/rtfd/sphinx_rtd_theme) provided by [Read the Docs](https://readthedocs.org). 
