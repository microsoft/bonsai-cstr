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

inkling "2.0"

using Math
using Goal

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

simulator CSTRSimulator(Action: SimAction, Config: SimConfig): SimState {
    # Automatically launch the simulator with this registered package name.
    #package "CSTR-20220106"
    #package "CSTR_Python_sim"
}

# Define a concept graph with a single concept
graph (input: ObservableState) {
    concept ModifyConcentration(input, ImportedConcept): SimAction {
        curriculum {

            algorithm {
                Algorithm: "PPO",
            }

            source CSTRSimulator

            training {
                EpisodeIterationLimit: 26,
                NoProgressIterationLimit: 600000
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

                    Cref_signal: number<1>,
                    noise_percentage: number<0 .. 5>,
                }
            }
        }
    }

    concept SteadyState(input): SimAction {
        curriculum {
            algorithm {
                Algorithm: "PPO",
            }

            source CSTRSimulator

            training {
                EpisodeIterationLimit: 130
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

            lesson `Lesson 1` {
                scenario {
                    # > 2: Steady state --> C = 8.57 , T = 311.2612
                    # > 3: Steady state --> C = 2 , T = 373.1311

                    Cref_signal: number<2 .. 3 step 1>,
                    noise_percentage: number<0 .. 100>,
                }
            }
        }
    }

    concept ImportedConcept(input): SimAction {
        import {
            Model: "cstr_temperature_model_rf"
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
                minimize `Concentration Reference`:
                    Math.Abs(State.Cref - State.Cr)
                    in Goal.RangeBelow(0.25)
                avoid `Thermal Runaway`:
                    Math.Abs(State.Tr)
                    in Goal.RangeAbove(400)
            }

            lesson `Lesson 1` {
                scenario {
                    # > 1: Concentration transition --> 8.57 to 2.000 over [0, 10, 36, 45] (minutes) - 0
                    # > 2: Concentration transition --> 8.57 to 2.000 over [0, 0, 26, 45] (minutes) - 10 sec delay (original)
                    # > 3: Concentration transition --> 8.57 to 2.000 over [0, 10, 20, 45] (minutes) - 20 sec delay
                    # > 4: Concentration transition --> 8.57 to 1.000 over [0, 10, 36, 45] (minutes) - 30 sec delay

                    Cref_signal: number<4>,
                    noise_percentage: number<0 .. 5>,
                }
            }
        }
    }
}
