"""Pytest configuration and setup of shared fixtures."""

import pytest
from pathlib import Path
from typing import Generator
from tempfile import TemporaryDirectory
import xarray as xr
import numpy as np

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    with TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_parameter_file(temp_dir: Path) -> Path:
    parameter_ranges_ini_content = """
    [test_parameter1]
    esm_component = CAM
    sampling = linear
    ndigits = 5
    max = 0.005
    min = 0.002
    default= 0.0034

    [test_parameter2]
    esm_component = CAM
    sampling = linear
    ndigits = 2
    max = 100
    min = 10
    default= 50

    [test_parameter3]
    esm_component = CAM
    sampling = log
    max = 30
    min= 0.1
    ndigits = 3
    default= 5.0
    interdependent_with = None

    [test_parameter4]
    esm_component = CLM
    sampling = linear
    default = 0.025
    scale_fact = 0.5
    ndigits = 4

    [d_max]
    esm_component = CLM
    sampling = linear
    ndigits = 2
    max = 20.0
    min = 5.0
    default= 13.0
    input_type = CTSM_param_file

    [frac_sat_soil_dsl_init]
    esm_component = CLM
    sampling = linear
    ndigits = 3
    max = 1.0
    min = 0.0
    default= 0.5
    input_type = CTSM_param_file

    [SOA_y_scale_chem_mech_in]
    esm_component = CAM
    description = Scale both SOA_y_isop and SOA_y_monoterp
    default = 1
    min = 0.2
    max = 2
    sampling = linear
    ndigits = 2
    """
    parameter_file_path = temp_dir / "test_ppe.ini"
    parameter_file_path.write_text(parameter_ranges_ini_content)
    return parameter_file_path


@pytest.fixture
def sample_usr_nl_ini(temp_dir: Path) -> Path:
    usr_nl_cam_sample_content = """
    [oslo_ctl_nl]
    use_aerocom = .false.

    [cam_history_nl]
    interpolate_nlat   = 96
    interpolate_nlon   = 144
    interpolate_output = .true.

    [phys_ctl_nl]
    history_aerosol = .false.

    [zmconv_nl]
    zmconv_c0_lnd   = 0.0075D0
    zmconv_ke       = 5.0E-6
    zmconv_ke_lnd   = 1.0E-5
    """
    usr_nl_ini_path = temp_dir / "control_cam_test.ini"
    usr_nl_ini_path.write_text(usr_nl_cam_sample_content)
    return usr_nl_ini_path

@pytest.fixture
def sample_ctsm_paramfile(temp_dir: Path) -> Path:
    """Create a sample CTSM parameter file for testing."""
    ds = xr.Dataset(data_vars={'d_max': np.array(13.0), 
                               'frac_sat_soil_dsl_init': np.array(0.5),
                               })
    paramfile_path = temp_dir / "ctsm_paramfile.nc"
    ds.to_netcdf(paramfile_path)
    return paramfile_path

@pytest.fixture
def sample_chem_mech_file(temp_dir: Path) -> Path:
    """Create a sample chemistry mechanism file for testing."""
    chem_mech_content = """
    *BEGSIM
    SPECIES

        Solution
    SO2, H2SO4
    DMS -> CH3SCH3, H2O2
    SO4_NA->H2SO4, SO4_A1->H2SO4, SO4_A2->NH4HSO4
    SO4_AC->H2SO4, SO4_PR->H2SO4, BC_N->C
    BC_AX->C, BC_NI->C, BC_A->C, BC_AI->C
    BC_AC->C, OM_NI->C, OM_AI->C, OM_AC->C
    DST_A2->AlSiO5, DST_A3->AlSiO5
    SS_A1->NaCl, SS_A2->NaCl, SS_A3->NaCl
    * Approximate soa species with those of monoterpene oxidation products
    * based on Paasonen et al. (2010); Taipale et al. (2008).
    SOA_NA->C10H16O2, SOA_A1->C10H16O2
    SOA_LV ->C10H16O2, SOA_SV->C10H16O2
    monoterp -> C10H16, isoprene -> C5H8
    H2O
    End Solution

        Fixed
    M, N2, O2, O3, OH, NO3, HO2
        End Fixed

        Col-int
    O3 = 0.
    O2 = 0.
        End Col-int

    End SPECIES

    Solution Classes
        Explicit
        End Explicit
        Implicit
            DMS, SO2, H2O2
            SO4_NA, SO4_A1, SO4_A2
            SO4_AC, SO4_PR, BC_N
            BC_AX, BC_NI, BC_A, BC_AI
            BC_AC, OM_NI, OM_AI, OM_AC
            DST_A2, DST_A3
            SS_A1, SS_A2, SS_A3 , H2SO4
            SOA_NA, SOA_A1
        SOA_LV,SOA_SV, monoterp, isoprene
            H2O
        End Implicit
    End Solution Classes

    CHEMISTRY
        Photolysis
    [jh2o2]    H2O2 + hv ->
        End Photolysis

        Reactions
    [usr_HO2_HO2] HO2 + HO2 -> H2O2
                H2O2 + OH -> H2O + HO2                                           ; 2.9e-12, -160
                DMS + OH -> SO2                                                  ; 9.6e-12, -234.
                DMS + NO3 -> SO2 + HNO3                                          ; 1.9e-13,  520.
                SO2 + OH + M -> H2SO4 + M                                      ; 3.0e-31, 3.3, 1.5e-12, 0.0, 0.6
    * SOA has MW=168, and MSA=96, so to get correct MSA mass ==> factor of 96/168 = 0.57
    * Then account for 0.25 which is 0.25 MSA molec per DMS molec (the other 0.75 goes to SO2)
    * Then 0.2 assumed yield for SOA_LV and 0.8 assumed  yield for SOA_SV gives the coefficients below
    * reaction rate from Chin et al 1996, JGR, vol 101, no D13
    *
    [usr_DMS_OH]  DMS + OH -> .75 * SO2 + .5 * HO2 + 0.029*SOA_LV + 0.114*SOA_SV
    *
    *cka: added organic vapor oxidation with constants from IUPAC below
    *     Assume a  yield of 15% for SOA LV production from these reactions
    *     Assume a  yield of 15 % for monoterpene and 5% for isoprene SOA SV production reactions
    *     SOA_LV: very low volatility, can nucleate or grow small particles (oxidation products from O3+monoterp)
    *     SOA_SV: rest of SOA formed
            monoterp + O3 -> 0.034*SOA_LV 			; 8.05e-16, -640.
            monoterp + OH -> 0.034*SOA_SV			; 1.2e-11, 440.
            monoterp + NO3 -> 0.034*SOA_SV			; 1.2e-12, 490.
            isoprene + O3 -> 0.011*SOA_SV			; 1.03e-14, -1995.
            isoprene + OH -> 0.011*SOA_SV 			; 2.7e-11, 390.
            isoprene + NO3 -> 0.011*SOA_SV 			; 3.15e-12, -450.
        End Reactions

        Heterogeneous
            H2O2, SO2
        End Heterogeneous

        Ext Forcing
            SO2 <- dataset
            BC_NI <-dataset
            BC_AX <-dataset
            BC_N <-dataset
            OM_NI <-dataset
            SO4_PR <-dataset
            H2O <- dataset
        End Ext Forcing

    END CHEMISTRY

    SIMULATION PARAMETERS

        Version Options
            model   = cam
            machine = intel
            architecture = hybrid
            vec_ftns  = on
            multitask = on
            namemod = on
            modules = on
        End Version Options

    END SIMULATION PARAMETERS
    *ENDSIM
    """
    chem_mech_file_path = temp_dir / "chem_mech.in"
    chem_mech_file_path.write_text(chem_mech_content)
    return chem_mech_file_path