# Repository description

## config_examples

The purpose of this directory is provide templates that are general purpose and can be further customized for different types PPE's within a model version. 

Current content:

* `config_examples/coupled_ppe_parameter_info.ini` - .ini files defining parameter ranges, describing their meaning, and the parameter default values. This is taken from one of the ongoing coupled PPE experiments and ranges here are subject to change as the model develops.

* `config_examples/default_control_atm.ini` and `config_examples/default_control_atm.ini` - Examples on how the `user_nl_` files might be specified, made to as closely mimic how user_nl_ files are specified in the standard case directory.

* `config_examples/default_simulation_setup.ini` - Example of a setup file containing information about compset and changes made via ./xmlchange, e.g., simulation time start date etc. 

## usermods

The purpose of this directory is keep different "usermods" show casing the different ongoing PPE activities. 

Currently the following PPEs are described under **usermods**:
- aerosol_ppe

## Other directories:

- **docs** Here is the documentation, any suggestions and improvements are very welcome. 
- **tests**  Testing of the code, testing is continuously being added to ensure that new functionality does not break existing parts of the toolkit.
- **tinkertool** The main source code of the tinkertool toolkit.  
