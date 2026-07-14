# Fetched: https://www.rapidwright.io/docs/RWRoute_timing_driven_routing.html
- final_url: https://www.rapidwright.io/docs/RWRoute_timing_driven_routing.html
- status: 200
- chars: 23414

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
    * RWRoute Timing-driven Routing
      * Steps to Run
      * Example Output
      * Validation with Vivado
    * [RWRoute Wirelength-driven Routing](https://www.rapidwright.io/docs/RWRoute_wirelength_driven_routing.html)
    * [RWRoute Partial Routing](https://www.rapidwright.io/docs/RWRoute_partial_routing.html)
    * [RapidWright Report Timing Example](https://www.rapidwright.io/docs/ReportTimingExample.html)
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
  * RWRoute Timing-driven Routing
  * [ View page source](https://www.rapidwright.io/docs/_sources/RWRoute_timing_driven_routing.rst.txt)



* * *

# RWRoute Timing-driven Routing¶

Routes an example design (](https://www.rapidwright.io/docs/e.g. “gnl_2_4_7_3.0_gnl_3500_03_7_80_80.dcp”).

This example was designed to show the default way to use RWRoute in the timing-driven mode and validate routing results with Vivado.

## Steps to Run¶

  1. Download the example [`gnl_2_4_7_3.0_gnl_3500_03_7_80_80.dcp`](https://www.rapidwright.io/docs/_downloads/0e4a69129c78826b68b971bfa2402840/gnl_2_4_7_3.0_gnl_3500_03_7_80_80.dcp) design:



    
    
    wget http://www.rapidwright.io/docs/_downloads/gnl_2_4_7_3.0_gnl_3500_03_7_80_80.dcp
    

  2. Invoke RWRoute via gradle (](https://www.rapidwright.io/docs/this will ensure code is compiled before running):



    
    
    rapidwright RWRoute gnl_2_4_7_3.0_gnl_3500_03_7_80_80.dcp gnl_2_4_7_3.0_gnl_3500_03_7_80_80_routed.dcp
    

The main entry point of RWRoute is `RWRoute.java` and is reproduced here for convenience:
    
    
    /**
     * The main interface of RWRoute that reads in a design checkpoint,
     * and parses the arguments for the RWRouteConfig Object of the router.
     * It instantiates a RWRoute Object or a PartialRouter Object
     * based on the partialRouting parameter and calls the route method to route the design.
     * @param args An array of strings that are used to create a RWRouteConfig Object for the router.
     */
    public static void main(](https://www.rapidwright.io/docs/String[] args) {
            if(](https://www.rapidwright.io/docs/args.length < 2){
        System.out.println(](https://www.rapidwright.io/docs/"USAGE: <input.dcp> <output.dcp>");
        return;
    }
    // Reads the output directory and set the output design checkpoint file name
    String routedDCPfileName = args[1];
    
            CodePerfTracker t = new CodePerfTracker(](https://www.rapidwright.io/docs/"RWRoute", true);
    
            // Reads in a design checkpoint and routes it
            Design routed = RWRoute.routeDesignWithUserDefinedArguments(](https://www.rapidwright.io/docs/Design.readCheckpoint(args[0]), args);
    
            // Writes out the routed design checkpoint
            routed.writeCheckpoint(](https://www.rapidwright.io/docs/routedDCPfileName,t);
            System.out.println(](https://www.rapidwright.io/docs/"\nINFO: Write routed design\n " + routedDCPfileName + "\n");
    }
    

Please refer to the documentation [Javadoc](http://www.rapidwright.io/javadoc/index.html) and code for more implementation details. The Java source code for RWRoute is located in: [src/com/xilinx/rapidwright/rwroute/](https://github.com/Xilinx/RapidWright/tree/master/src/com/xilinx/rapidwright/rwroute).

## Example Output¶

Example output using the `gnl_2_4_7_3.0_gnl_3500_03_7_80_80.dcp` design is included below:
    
    
    ==============================================================================
    ==                                 RWRoute                                  ==
    ==============================================================================
    ==============================================================================
    ==            Reading DCP: gnl_2_4_7_3.0_gnl_3500_03_7_80_80.dcp            ==
    ==============================================================================
     XML Parse & Device Load:     2.593s
                      EDIF Parse:     1.003s
                Read XDEF Header:     0.026s
                Read XDEF Caches:     0.045s
             Read XDEF Placement:     1.900s
               Read XDEF Routing:     0.071s
    ------------------------------------------------------------------------------
                 [No GC] *Total*:     5.638s
    ==============================================================================
    ==                               Route Design                               ==
    ==============================================================================
    INFO: Route 2123 pins of GLOBAL_LOGIC1
    INFO: Estimated pre-routing max delay: 1969
    ------------------------------------------------------------------------------
                      Generated       RRG        Routed  Nodes With     CPD  Total Run
    Iteration     RRG Nodes  Time (](https://www.rapidwright.io/docs/s)   Connections    Overlaps    (](https://www.rapidwright.io/docs/ps)   Time (](https://www.rapidwright.io/docs/s)
    ---------  ----------------------   -----------  ----------   -----  ---------
       1             238180      1.56         14952        3804    2469       2.32
       2              14115      0.11          6923        2366    2308       0.71
       3              14333      0.10          5103        1354    2308       0.83
       4              14207      0.10          2933         542    2308       0.71
       5              12593      0.09          1169         119    2323       0.66
       6              11313      0.05           274           6    2331       0.29
       7                587      0.00            56           0    2331       0.10
    ------------------------------------------------------------------------------
    
    INFO: Route 0 direct connections
    
    INFO: No PIP overlaps
    
    ==============================================================================
    ==                                Statistics                                ==
    ==============================================================================
    Total wirelength:                        12860
    Route design:                            8.21s
    ├─ Initialization:                       1.95s
    └─ Routing:                              6.26s
    ==============================================================================
    ==                              Timing Report                               ==
    ==============================================================================
    Timing requirement (](https://www.rapidwright.io/docs/ps):                  3000
    Critical path delay (](https://www.rapidwright.io/docs/ps):                 2331
    Slack (](https://www.rapidwright.io/docs/ps):                                669
    With timing closure guarantee:
    Critical path delay (](https://www.rapidwright.io/docs/ps):                 2500
    Slack (](https://www.rapidwright.io/docs/ps):                                500
    
    Detail delays:
    ------------------------------------------------------------------------------
    Logic (](https://www.rapidwright.io/docs/ps)  Net (](https://www.rapidwright.io/docs/ps)  (](https://www.rapidwright.io/docs/intrasite (ps))  Total (](https://www.rapidwright.io/docs/ps)    Netlist Resource(](https://www.rapidwright.io/docs/s)
    ----------  --------------------------  ----------    ------------------------
                 0         0                 0           0    superSource
                78       451                 0         529    FD_n/Q
                                                              net: opr[57]
                90         0                 0          90    LUT5_1b7/I0
                 0        53                 0          53    LUT5_1b7/O
                                                              net: nfd6
               125         0                 0         125    LUT3_1b6/I1
                 0       193                 0         193    LUT3_1b6/O
                                                              net: nfd7
                35         0                 0          35    LUT5_1bd/I3
                 0       137                 0         137    LUT5_1bd/O
                                                              net: n100c
               115         0                 0         115    LUT6_2_a4/LUT5/I2
                 0       242                60         242    LUT6_2_a4/LUT5/O
                                                              net: LUT6_2_a4/O5
               115         0                 0         115    LUT6_2_a5/LUT5/I2
                 0       253                60         253    LUT6_2_a5/LUT5/O
                                                              net: LUT6_2_a5/O5
               100         0                 0         100    LUT5_1bc/I3
                 0       194                60         194    LUT5_1bc/O
                                                              net: n1012
               100         0                 0         100    LUT2_1b5/I1
                 0        50                50          50    LUT2_1b5/O
                                                              net: nfea
                 0         0                 0           0    FD_jmm/D
    ----------  --------------------------  ----------    ------------------------
    Arrival time:                                 2331
    ------------------------------------------------------------------------------
    ==============================================================================
                      Write EDIF:     0.145s
             Writing XDEF Header:     0.195s
      Writing XDEF Placement:     0.367s
            Writing XDEF Routing:     0.453s
     Writing XDEF Finalizing:     0.030s
                     Writing XDC:     0.006s
    ------------------------------------------------------------------------------
                 [No GC] *Total*:     1.196s
    
    INFO: Write routed design
     gnl_2_4_7_3.0_gnl_3500_03_7_80_80_routed.dcp
    

The output contains four main sections regarding reading the design checkpoint, RWRoute processing info, routing statistics, and timing report. The log file shows that RWRoute successfully routes the design. The originally calculated critical path delay is 2331 ps and it has been adjusted to 2500 ps through a pessimistic approach.

## Validation with Vivado¶

To validate the routed design by Vivado, run the following at the prompt:
    
    
    vivado -mode tcl gnl_2_4_7_3.0_gnl_3500_03_7_80_80_routed.dcp
    

and then run the following command at the Vivado Tcl prompt:
    
    
    report_route_status
    

The resulting output should show the design is successfully routed, as all the routable nets are fully routed and there is no nets with routing errors.
    
    
    Design Route Status
                                                :      # nets :
    ------------------------------------------- : ----------- :
    # of logical nets.......................... :        4937 :
        # of nets not needing routing.......... :        1082 :
            # of internally routed nets........ :         932 :
            # of implicitly routed ports....... :         150 :
        # of routable nets..................... :        3855 :
            # of fully routed nets............. :        3855 :
        # of nets with routing errors.......... :           0 :
    ------------------------------------------- : ----------- :
    

In Vivado 2020.1, the timing report shows that the design routed by RWRouote has a data path delay of 2.331 ns (](https://www.rapidwright.io/docs/2331 ps) for the same critical path. The full Vivado timing report is shown below:
    
    
    -----------------------------------------------------------------------------------------
    | Tool Version      : Vivado v.2020.1 (](https://www.rapidwright.io/docs/lin64) Build 2902540 Wed May 27 19:54:35 MDT 2020
    | Date              : Mon Nov  8 22:20:55 2021
    | Host              : yun-Latitude-3470 running 64-bit Ubuntu 16.04.7 LTS
    | Command           : report_timing
    | Design            : gnl_3500_03_7_80_80
    | Device            : xcvu3p-ffvc1517
    | Speed File        : -2  PRODUCTION 1.27 02-28-2020
    | Temperature Grade : E
    -----------------------------------------------------------------------------------------
    
    Timing Report
    
    Slack (](https://www.rapidwright.io/docs/MET) :             0.649ns  (](https://www.rapidwright.io/docs/required time - arrival time)
      Source:                 FD_n/C
                                    (](https://www.rapidwright.io/docs/rising edge-triggered cell FDRE clocked by clk  {rise@0.000ns fall@1.500ns period=3.000ns})
      Destination:            FD_jmm/D
                                    (](https://www.rapidwright.io/docs/rising edge-triggered cell FDRE clocked by clk  {rise@0.000ns fall@1.500ns period=3.000ns})
      Path Group:             clk
      Path Type:              Setup (](https://www.rapidwright.io/docs/Max at Slow Process Corner)
      Requirement:            3.000ns  (](https://www.rapidwright.io/docs/clk rise@3.000ns - clk rise@0.000ns)
      Data Path Delay:        2.331ns  (](https://www.rapidwright.io/docs/logic 0.753ns (32.304%)  route 1.578ns (](https://www.rapidwright.io/docs/67.696%))
      Logic Levels:           7  (](https://www.rapidwright.io/docs/LUT2=1 LUT3=1 LUT5=5)
      Clock Path Skew:        -0.010ns (](https://www.rapidwright.io/docs/DCD - SCD + CPR)
            Destination Clock Delay (](https://www.rapidwright.io/docs/DCD):    0.020ns = (](https://www.rapidwright.io/docs/3.020 - 3.000 )
            Source Clock Delay      (](https://www.rapidwright.io/docs/SCD):    0.030ns
            Clock Pessimism Removal (](https://www.rapidwright.io/docs/CPR):    0.000ns
      Clock Uncertainty:      0.035ns  (](https://www.rapidwright.io/docs/(TSJ^2 + TIJ^2)^1/2 + DJ) / 2 + PE
            Total System Jitter     (](https://www.rapidwright.io/docs/TSJ):    0.071ns
            Total Input Jitter      (](https://www.rapidwright.io/docs/TIJ):    0.000ns
            Discrete Jitter          (](https://www.rapidwright.io/docs/DJ):    0.000ns
            Phase Error              (](https://www.rapidwright.io/docs/PE):    0.000ns
    
            Location             Delay type                Incr(](https://www.rapidwright.io/docs/ns)  Path(](https://www.rapidwright.io/docs/ns)    Netlist Resource(](https://www.rapidwright.io/docs/s)
      -------------------------------------------------------------------    -------------------
                                 (](https://www.rapidwright.io/docs/clock clk rise edge)        0.000     0.000 r
                                                              0.000     0.000 r  clk (](https://www.rapidwright.io/docs/IN)
                                 net (](https://www.rapidwright.io/docs/fo=1161, unset)         0.030     0.030    clk
            SLICE_X22Y115        FDRE                                         r  FD_n/C
      -------------------------------------------------------------------    -------------------
            SLICE_X22Y115        FDRE (](https://www.rapidwright.io/docs/Prop_DFF_SLICEM_C_Q)
                                                              0.078     0.108 r  FD_n/Q
                                 net (](https://www.rapidwright.io/docs/fo=21, routed)          0.523     0.631    opr[57]
            SLICE_X14Y100        LUT5 (](https://www.rapidwright.io/docs/Prop_G6LUT_SLICEL_I0_O)
                                                              0.089     0.720 r  LUT5_1b7/O
                                 net (](https://www.rapidwright.io/docs/fo=2, routed)           0.050     0.770    nfd6
            SLICE_X14Y100        LUT3 (](https://www.rapidwright.io/docs/Prop_B6LUT_SLICEL_I1_O)
                                                              0.124     0.894 r  LUT3_1b6/O
                                 net (](https://www.rapidwright.io/docs/fo=19, routed)          0.226     1.120    nfd7
            SLICE_X13Y95         LUT5 (](https://www.rapidwright.io/docs/Prop_F6LUT_SLICEM_I3_O)
                                                              0.037     1.157 r  LUT5_1bd/O
                                 net (](https://www.rapidwright.io/docs/fo=4, routed)           0.139     1.296    LUT6_2_a4/I2
            SLICE_X14Y95         LUT5 (](https://www.rapidwright.io/docs/Prop_C5LUT_SLICEL_I2_O)
                                                              0.110     1.406 r  LUT6_2_a4/LUT5/O
                                 net (](https://www.rapidwright.io/docs/fo=8, routed)           0.219     1.625    LUT6_2_a5/I2
            SLICE_X14Y95         LUT5 (](https://www.rapidwright.io/docs/Prop_B5LUT_SLICEL_I2_O)
                                                              0.116     1.741 r  LUT6_2_a5/LUT5/O
                                 net (](https://www.rapidwright.io/docs/fo=2, routed)           0.213     1.954    n100f
            SLICE_X14Y95         LUT5 (](https://www.rapidwright.io/docs/Prop_A5LUT_SLICEL_I3_O)
                                                              0.100     2.054 r  LUT5_1bc/O
                                 net (](https://www.rapidwright.io/docs/fo=2, routed)           0.157     2.211    n1012
            SLICE_X14Y95         LUT2 (](https://www.rapidwright.io/docs/Prop_H6LUT_SLICEL_I1_O)
                                                              0.099     2.310 r  LUT2_1b5/O
                                 net (](https://www.rapidwright.io/docs/fo=1, routed)           0.051     2.361    nfea
            SLICE_X14Y95         FDRE                                         r  FD_jmm/D
      -------------------------------------------------------------------    -------------------
    
                                 (](https://www.rapidwright.io/docs/clock clk rise edge)        3.000     3.000 r
                                                              0.000     3.000 r  clk (](https://www.rapidwright.io/docs/IN)
                                 net (](https://www.rapidwright.io/docs/fo=1161, unset)         0.020     3.020    clk
            SLICE_X14Y95         FDRE                                         r  FD_jmm/C
                                 clock pessimism              0.000     3.020
                                 clock uncertainty           -0.035     2.985
            SLICE_X14Y95         FDRE (](https://www.rapidwright.io/docs/Setup_HFF_SLICEL_C_D)
                                                              0.025     3.010    FD_jmm
      -------------------------------------------------------------------
                                 required time                          3.010
                                 arrival time                          -2.361
      -------------------------------------------------------------------
                                 slack                                  0.649
    

It should be noted that the critical path reported by Vivado can be different from that of RWRoute for the same routed design. This is reasonable, as they use different timing models. The main point is that RWRoute is able to estimate a similar critical path delay to that of Vivado timing analysis.

[Next ](https://www.rapidwright.io/docs/RWRoute_wirelength_driven_routing.html "RWRoute Wirelength-driven Routing") [ Previous](https://www.rapidwright.io/docs/Tutorials.html "RapidWright Tutorials")

* * *

(](https://www.rapidwright.io/docs/C) Copyright 2018-2026, Advanced Micro Devices, Inc. 

Built with [Sphinx](http://sphinx-doc.org/) using a [theme](https://github.com/rtfd/sphinx_rtd_theme) provided by [Read the Docs](https://readthedocs.org). 
