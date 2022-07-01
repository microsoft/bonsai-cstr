# MSFT Bonsai
# Copyright 2022 Microsoft
# This code is licensed under MIT license (see LICENSE for details)

# Overview
# The process considered here is a Continuous Stirred Tank Reactor (CSTR) during transition from
# low to high conversion rate (high to low residual concentration). Because the chemical reaction
# is exothermic (produces heat), the reactor temperature must be controlled to prevent a thermal
# runaway. The control task is complicated by the fact that the process dynamics are nonlinear and
# transition from stable to unstable and back to stable as the conversion rate increases. The reactor
# dynamics are modeled in Simulink. The controlled variables (states) are the residual concentration Cr
# and the reactor temperature Tr, and the manipulated variable (action) is the temperature Tc of the
# coolant circulating in the reactor's cooling jacket.

# More details about the model are available at https://aka.ms/bonsai-chemicalprocessing

# The Chemical Processing example is part of the Project Bonsai Simulink Toolbox
# and can be downloaded from https://aka.ms/bonsai-toolbox

inkling "2.0"

using Math
using Goal

#const SimulatorVisualizer = "https://scotstan.github.io/bonsai-viz-example/debug"
const SimulatorVisualizer = "https://jralexander.github.io/bonsai-viz-example/gauges"

const Ts = 0.5 # Sim Period
const coolant_temp_deriv_limit_per_min = 10 # Coolant temperature derivative limit per minute
#const coolant_temp_deriv_limit = Ts * coolant_temp_deriv_limit_per_min
const coolant_temp_deriv_limit = coolant_temp_deriv_limit_per_min

# Limits for concentration
const conc_max = 12
const conc_min = 0.1

# Limits for reactor temperature
const temp_max = 800
const temp_min = 10

# State received from the simulator after each iteration
type SimState {
    # Concentration: Real-time reactor read
    Cr: number<conc_min .. conc_max>,
    # Temperature: Real-time reactor read
    Tr: number<temp_min .. temp_max>,

    # Concentration: Target reference to follow
    Cref: number<conc_min .. conc_max>,
    # Temperature: Target reference to follow
    Tref: number<temp_min .. temp_max>,

    # Coolant absolute temperature as input to the simulation
    Tc: number<temp_min .. temp_max>,
}


# State which are used to train brain
# - set of states that the brain will have access to when deployed -
type ObservableState {
    # Concentration: Real-time reactor read
    Cr: number<conc_min .. conc_max>,

    # Temperature: Real-time reactor read
    Tr: number<temp_min .. temp_max>,

    # Concentration: Target reference to follow
    Cref: number<conc_min .. conc_max>,

    # Coolant absolute temperature as input to the simulation
    Tc: number<temp_min .. temp_max>,

}

# Action provided as output by policy and sent as
# input to the simulator
type SimAction {
    # Delta to be applied to initial coolant temp (absolutely, not per-iteration)
    Tc_adjust: number<-coolant_temp_deriv_limit .. coolant_temp_deriv_limit>
}

# Per-episode configuration that can be sent to the simulator.
# All iterations within an episode will use the same configuration.
type SimConfig {
    # Scenario to be run - 4 scenarios: 1-based INT
    # > 1: Concentration transition --> 8.57 to 2.000 over 26 (minutes) - 0 delay
    # > 2: Steady state --> C = 8.57 , T = 311.2612
    # > 3: Steady state --> C = 2 , T = 373.1311
    # > 4: Steady state and Transition --> 8.57 to 2.000 over 45 (minutes) - 22 delay
    Cref_signal: number<1 .. 4 step 1>,

    # Percentage of noise to include
    noise_percentage: number<0 .. 100>
}

type ImportedOutputState {

    out: number,

}

simulator CSTRSimulator(Action: SimAction, Config: SimConfig): SimState {
    # Automatically launch the simulator with this registered package name.
    #package "CSTR-20220106"
    #package "CSTR_Python_sim"
}


# Define a concept graph 
graph (input: ObservableState) {
    concept ModifyConcentration(input): SimAction {
        curriculum {

            algorithm {
                Algorithm: "PPO",
            }

            source CSTRSimulator

            training {
                EpisodeIterationLimit: 90,
                NoProgressIterationLimit: 1000000
            }

            # The objective of training is expressed as 2 goals
            # (1) drive concentration close to reference
            # (2) avoid temperature going beyond limit
            goal (State: SimState) {
                minimize `Concentration Reference`:
                    Math.Abs(State.Cref - State.Cr)
                    in Goal.RangeBelow(0.25)
                avoid `Thermal Runaway`:
                    Math.Abs(State.Tr)
                    in Goal.RangeAbove(400)
            }

            lesson `Follow Planned Concentration` {
                # Specify the configuration parameters that should be varied
                # from one episode to the next during this lesson.
                scenario {
                    # > 1: Concentration transition --> 8.57 to 2.000 over 26 (minutes) - 0 delay

                    Cref_signal: number<4>,
                    noise_percentage: number<0 .. 0.05>,
                }
            }
        }
    }
}



#! Visual authoring information
#! eyJ2ZXJzaW9uIjoiMi4wLjAiLCJ2aXN1YWxpemVycyI6eyJTaW11bGF0b3JWaXN1YWxpemVyIjoiaHR0cHM6Ly9qcmFsZXhhbmRlci5naXRodWIuaW8vYm9uc2FpLXZpei1leGFtcGxlL2dhdWdlcyJ9LCJnbG9iYWwiOnsidmlzdWFsaXplck5hbWVzIjpbIlNpbXVsYXRvclZpc3VhbGl6ZXIiXX0sImNvbmNlcHRzIjp7Ik1vZGlmeUNvbmNlbnRyYXRpb24iOnsicG9zaXRpb25PdmVycmlkZSI6eyJ4IjoxMTUuMDAwNTkyNjc4MjkxMTgsInkiOjM2OX19LCJTdGVhZHlTdGF0ZSI6eyJwb3NpdGlvbk92ZXJyaWRlIjp7IngiOjI0LjAwMDgxMzM2MDA2MzY2LCJ5IjoyMzB9fSwiU2VsZWN0U3RyYXRlZ3kiOnsicG9zaXRpb25PdmVycmlkZSI6eyJ4IjoxNDUuMDAwOTQ1ODM2MzI2MzQsInkiOjUxMX19LCJJbXBvcnRlZENvbmNlcHRUZXN0Ijp7InBvc2l0aW9uT3ZlcnJpZGUiOnsieCI6LTg2Ljk5OTA2MzQ5NTkzMjgzLCJ5Ijo3NH19LCJQcm9ncmFtbWVkQ29uY2VwdFRlc3QiOnsicG9zaXRpb25PdmVycmlkZSI6eyJ4IjoxMTguMDAwMzk0NjI1MTM3MDMsInkiOjc0NX19LCJTdGVhZHlTdGF0ZTIiOnsicG9zaXRpb25PdmVycmlkZSI6eyJ4IjoyMzIuMDAwODc2NjgyMzA0OCwieSI6MjI5fX19LCJvdXRwdXRUZW5zb3IiOnsicG9zaXRpb25PdmVycmlkZSI6eyJ4IjoyMDMuMDAwMDk0Nzk0Mjk3MTMsInkiOjg4NX19fQ==
