# Fetched: https://www.rapidwright.io/docs/FPGA_Interchange_Format.html
- final_url: https://www.rapidwright.io/docs/FPGA_Interchange_Format.html
- status: 200
- chars: 5447

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
  * FPGA Interchange Format
    * What is the FPGA Interchange Format?
    * What does the FPGA Interchange Format enable?
    * How is RapidWright related to the FPGA Interchange Format?
    * Additional Resources
  * [RapidWright Publications](https://www.rapidwright.io/docs/Papers.html)
  * [A Pre-implemented Module Flow](https://www.rapidwright.io/docs/PreImplemented_Module_Flow.html)
  * [RapidWright Tutorials](https://www.rapidwright.io/docs/Tutorials.html)
  * [Tech Articles](https://www.rapidwright.io/docs/Tech_Articles.html)
  * [Frequently Asked Questions](https://www.rapidwright.io/docs/FAQ.html)
  * [Glossary](https://www.rapidwright.io/docs/Glossary.html)



  
  
[Download PDF  
![](https://www.rapidwright.io/docs/_static/pdf.svg)](https://www.rapidwright.io/docs/RapidWright.pdf)   
  
  
[Javadoc API Reference  
![](https://www.rapidwright.io/docs/_static/javadoc.svg)](https://www.rapidwright.io/javadoc/index.html)

__[RapidWright Docs](https://www.rapidwright.io/docs/index.html)

  * [Docs](https://www.rapidwright.io/docs/index.html) »
  * FPGA Interchange Format
  * [ View page source](https://www.rapidwright.io/docs/_sources/FPGA_Interchange_Format.rst.txt)



* * *

# FPGA Interchange Format¶

## What is the FPGA Interchange Format?¶

The FPGA Interchange Format (](https://www.rapidwright.io/docs/FPGAIF) is a standard exchange format designed to provide all the information necessary to perform placement and routing in an open source context. It contains three major schemas that define how to transfer the following kinds of data in an architecture-independent way:

>   1. FPGA architecture device model: The available placement and programmable routing resources on the FPGA
> 
>   2. Logical netlist: Cell definitions, networks, pins, hierarchy, etc.
> 
>   3. Physical netlist: Placement mappings and routing configurations, i.e. mapping the logical netlist to the FPGA architecture device model
> 
> 


The FPGAIF is hosted as an [open source project](https://www.chipsalliance.org/projects/) under the [CHIPS Alliance](https://www.chipsalliance.org/) and original development was started in 2020.

## What does the FPGA Interchange Format enable?¶

Primarily it allows tools–both commercial and open source–an open way to exchange FPGA device and design data to enable customized place and route solutions. Some tools and efforts that support the FPGAIF:

>   * [DREAMPlaceFPGA](https://github.com/rachelselinar/DREAMPlaceFPGA) – An open source GPU accelerated FPGA placer (](https://www.rapidwright.io/docs/[FPGAIF Support Page](https:/github.com/rachelselinar/DREAMPlaceFPGA/tree/main/IFsupport))
> 
>   * [ISFPGA 2024 Runtime-first Routing Contest](https://xilinx.github.io/fpga24_routing_contest/)
> 
>   * [python-fpga-interchange](https://fpga-interchange-schema.readthedocs.io/) – A Python module for reading and writing FPGA Interchange Files
> 
>   * [RapidWright](https://github.com/Xilinx/RapidWright/tree/master/interchange) – Full support for all AMD-Xilinx architectures and design files
> 
> 


## How is RapidWright related to the FPGA Interchange Format?¶

RapidWright has a full reference implementation of the entire FPGA Interchange schema. It is able to generate nearly all supported FPGA devices in the format and can read and write Interchange designs. It can convert those designs to and from design checkpoint files to be exported and imported from Vivado.

## Additional Resources¶

>   * [AMD-Xilinx announcement of support for the FPGA Interchange Format](https://www.linkedin.com/pulse/chips-alliance-fpga-interchange-format-ivo-bolsens/?trackingId=or6MV42Xn5ixheYSpNrldA%3D%3D)
> 
>   * [Google Open Source Blog Article on the FPGA Interchange Format](https://opensource.googleblog.com/2022/02/FPGA%20Interchange%20format%20to%20enable%20interoperable%20FPGA%20tooling.html)
> 
>   * [ReadTheDocs Documentation for the FPGA Interchange Schema](https://fpga-interchange-schema.readthedocs.io/)
> 
>   * [FPGA Interchange Schema GitHub Repository](https://github.com/chipsalliance/fpga-interchange-schema)
> 
> 


[Next ](https://www.rapidwright.io/docs/Papers.html "RapidWright Publications") [ Previous](https://www.rapidwright.io/docs/Bitstream_Manipulation.html "Bitstream Manipulation")

* * *

(](https://www.rapidwright.io/docs/C) Copyright 2018-2026, Advanced Micro Devices, Inc. 

Built with [Sphinx](http://sphinx-doc.org/) using a [theme](https://github.com/rtfd/sphinx_rtd_theme) provided by [Read the Docs](https://readthedocs.org). 
