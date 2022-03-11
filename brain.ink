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

# More details about the model are available at https://aka.ms/chemical-reactor-sample
# The Simulink model is available at https://github.com/microsoft/bonsai-cstr

# The similar Chemical Processing example is part of the Project Bonsai Simulink Toolbox
# and can be downloaded from https://aka.ms/bonsai-toolbox

inkling "2.0"

using Math
using Goal

const SimulatorVisualizer = "https://microsoft.github.io/bonsai-cstr/visualizer/gauges/"

const Ts = 0.5 # Sim Period
const coolant_temp_deriv_limit_per_min = 10 # Coolant temperature derivative limit per minute
const coolant_temp_deriv_limit = Ts * coolant_temp_deriv_limit_per_min

# Limits for concentration
const conc_max = 12
const conc_min = 0

# Limits for reactor temperature
const temp_max = 800
const temp_min = 10

# State received from the simulator after each iteration
type SimState {
    Cr: number<conc_min .. conc_max>,         # Concentration: Real-time reactor read
    Tr: number<temp_min .. temp_max>,         # Temperature: Real-time reactor read
    Cref: number<conc_min .. conc_max>,       # Concentration: Target reference to follow
    Tref: number<temp_min .. temp_max>,       # Temperature: Target reference to follow
    Tc: number<temp_min .. temp_max>,         # Coolant absolute temperature as input to the simulation
}

# State which are used to train brain
type ObservableState {
    Cr: number<conc_min .. conc_max>,         # Concentration: Real-time reactor read
    Tr: number<temp_min .. temp_max>,         # Temperature: Real-time reactor read
    Cref: number<conc_min .. conc_max>,       # Concentration: Target reference to follow
    Tc: number<temp_min .. temp_max>,         # Coolant absolute temperature as input to the simulation
}

# Action provided as output by policy and sent as to the simulator
type SimAction {
    # Delta to be applied to initial coolant temp (absolutely, not per-iteration)
    Tc_adjust: number<-coolant_temp_deriv_limit .. coolant_temp_deriv_limit>
}

# Per-episode configuration that can be sent to the simulator.
# All iterations within an episode will use the same configuration.
type SimConfig {
    # Scenario to be run - 5 scenarios: 1-based INT
    # > 1: Concentration transition --> 8.57 to 2.000 - 0 min delay
    # > 2: Concentration transition --> 8.57 to 2.000 - 10 min delay 
    # > 3: Concentration transition --> 8.57 to 2.000 - 20 min delay
    # > 4: Concentration transition --> 8.57 to 2.000 - 30 min delay
    # > 5: Steady State --> 8.57
    Cref_signal: number<1 .. 5 step 1>,
    noise_percentage: number<0 .. 100>  # Percentage of noise to include
}

simulator CSTRSimulator(Action: SimAction, Config: SimConfig): SimState {
    # Automatically launch the simulator with this registered package name.

    # CSTR sim https://github.com/microsoft/bonsai-cstr SHA: 43f90d7
    package "CSTR"
}

# Define a concept graph with a single concept
graph (input: ObservableState) {
    concept ModifyConcentration(input): SimAction {
        curriculum {

            source CSTRSimulator

            training {
                EpisodeIterationLimit: 90,
                NoProgressIterationLimit: 500000
            }

            # The objective of training is expressed as 2 goals
            # (1) drive concentration close to reference
            # (2) avoid temperature going beyond limit
            goal (State: SimState) {
                minimize `Concentration Reference` weight 1:
                    Math.Abs(State.Cref - State.Cr)
                    in Goal.RangeBelow(0.25)
                avoid `Thermal Runaway` weight 4:
                    Math.Abs(State.Tr)
                    in Goal.RangeAbove(400)
            }

            lesson `Follow Planned Concentration` {
                # Specify the configuration parameters that should be varied
                # from one episode to the next during this lesson.
                scenario {
                    Cref_signal: number<1>, # Transition from 8.57 to 2 with no delay
                    noise_percentage: number<0 .. 5>,
                }
            }
        }
    }

    concept SteadyState(input): SimAction {
        curriculum {

            source CSTRSimulator

            training {
                EpisodeIterationLimit: 90
            }
            # The objective of training is expressed as 2 goals
            # (1) drive concentration close to reference
            # (2) avoid temperature going beyond limit
            goal (State: SimState) {
                minimize `Concentration Reference` weight 1:
                    Math.Abs(State.Cref - State.Cr)
                    in Goal.RangeBelow(0.25)
                avoid `Thermal Runaway` weight 4:
                    Math.Abs(State.Tr)
                    in Goal.RangeAbove(400)
            }

            lesson `Lesson 1` {
                scenario {
                    Cref_signal: number<5>, # Steady State of 8.57 kmol/m3
                    noise_percentage: number<0 .. 5>,
                }
            }
        }
    }

    output concept SelectStrategy(input): SimAction {
        select SteadyState
        select ModifyConcentration
        curriculum {

            source CSTRSimulator

            training {
                EpisodeIterationLimit: 90,
                NoProgressIterationLimit: 500000
            }
            # The objective of training is expressed as 2 goals
            # (1) drive concentration close to reference
            # (2) avoid temperature going beyond limit
            goal (State: SimState) {
                minimize `Concentration Reference` weight 1:
                    Math.Abs(State.Cref - State.Cr)
                    in Goal.RangeBelow(0.25)
                avoid `Thermal Runaway` weight 4:
                    Math.Abs(State.Tr)
                    in Goal.RangeAbove(400)
            }

            lesson `Lesson 1` {
                scenario {
                    Cref_signal: number<2 .. 4 step 1>, # Combinations of Steady State and Transient State
                    noise_percentage: number<0 .. 5>,
                }
            }
        }
    }
}