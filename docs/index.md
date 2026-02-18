# Welcome to NorESMTinkerTool
![logo](./img/logo.jpg)

> _A safe space for tinkering_
>

NorESMTinkerTool is a toolchain developed in Python for the development, building, production, and analysis of Perturbed Parameter Ensembles (PPEs) with the Norwegian Earth System Model (NorESM). The motivation for developing NorESMTinkerTool was to encourage more playful exploration of the model's parameter space by making tinkering with the model more accessible.

The toolchain leverages the CIME infrastructure for building and creating the perturbed parameter ensembles. Latin hyper cube sampling is used to distribute the ensemble members such that they span the parameter space most efficiently.

The NorESMTinkerTool have following functions, in parenthesis indicates maturity and progress of the development the specific feature. 

1. Generate parameter file for PPE ***(beta)***.
    - latin hyper cube sampling or one at the time test
2. Create PPE ***(pre-beta)***.
    - build ensemble members ***(beta)***
    - check build ***(alpha)***
    - prestage data ***(alpha)***
    - submit ppe to queue ***(alpha)***
3. Catalogue PPE ***(In development pre-alpha)***
    - build intake_esm catalog to organize history files ***(pre-alpha)***
4. Emulate PPE ***(Not started, help wanted)***
    - Gaussian Process emulation fill the gaps in the parameter space
5. Constrain PPE ***(Not started, help wanted)*** 
    - Constrain the PPE against observational constrains 


If you have ideas' and suggestions please have look at [contributing](contributing.md),  feedback or pull requests are very much appreciated.  

## 📚 Contents

- [Description of repository](description.md)
- [Installation](installation.md)
- [Configuration](configuration.md)
- [CLI](cli.md)
- [API Usage](usage.md)
- [API Reference](api.md)
- [Examples](examples.md)
- [FAQ](faq.md)
- [Contributing](contributing.md)
- [Changelog](changelog.md)