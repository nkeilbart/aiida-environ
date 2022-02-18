## v1.0.0:
First official release of `aiida-environ`, the plugin for Environ to the AiiDA platform.
The following calculations, data classes, parsers and workflows are provided:

### Calculations
- `EnvPwCalculation`: calculation plugin for `pw.x` with Environ

### Data
- `ForceconstantsData`: data class for force constants produced by `q2r.x` 

### Parsers
- `EnvPwParser`: parser for the `pw.x` calculation with Environ

### Workflows
- `EnvPwBaseWorkChain`: workflow to run a `EnvPwCalculation` to completion
- `EnvPwRelaxWorkChain`: performs geometry optimization with `EnvPwBaseWorkChain`
- `EnvPwForceWorkChain`: computes forces via finite differences with `EnvPwBaseWorkChain`
- `PwSolvationWorkChain`: computes solvation energy with `EnvPwBaseWorkChain`
