import traceback
import json
import os
import random
import ast
from scipy import interpolate
import math
from typing import Dict, Any, Union

from cstr_solver import CSTR_Solver as CSTR_Solver

import numpy as np
import sys

import matplotlib.pyplot as plt

from sim.log_feature import SimLogger

# time step (seconds) between state updates
Δt_sim = 1
thermal_runaway = 400
        # Max considered transition time (the simulation cannot run further).
max_simulation_time = 1000

# Known equilibrion relationships for concentration and temperature
Cr_eq = [8.57, 6.9275, 5.2850, 3.6425, 2]
Tr_eq = [311.2612, 327.9968, 341.1084, 354.7246, 373.1311]
# TODO: Add the equilibrium values for Tc_eq
Tc_eq = [292, 292, 292, 292, 292]

class CSTRSimulation():
    def __init__(
        self,
        render: bool = False,
        log_data: Union[bool, str] = False,
        debug: bool = True,
    ):
        """CSTR simulation using a python solver.

        Parameters
        ----------
        render : bool, optional
            # TODO: Add render functionality as a method to this class.
            render every control timestep of the environment, by default False
        log_data : bool/str, optional
            whether to MDP data to CSV, by default False.
            If str is provided, CSV name generation will use tag for unique identification.
        debug : bool, optional
            debugging functionality for in-depth debugging when requested.
        """
        
        self.render = render
        self.debug = debug

        # Logging features
        self.log_data = log_data
        self.sim_logger = SimLogger(log_data=self.log_data)

        # Initialize episodic config dict
        self.config = {}

    def reset(
        self,
        config: Dict[str, Any] = {},

        # Non-applicable initialization parameters during episode restart
        ΔTc: float = 0,
        Ca: float = 0,
        T: float = 0,
        Tc: float = 0,
        Cref: float = 0,
        Tref: float = 0,
        cnt: float = 0
    ):
        """
        Initialize a new episode of the simulator with configuration parameters.
        # TODO: Modify config to be a dictionary, instead of a set of independent arguments.

        Parameters
        ----------
        Cref_signal: Reference Cref & Tref to be followed by our control.
          Values that Cref_signal can take:
            (0) N/A  ---> STATIC: Cref == Tref == 0.
            (1) Transition from (Cref, Tref) of (8.57, 311.3) to (2, 373.1), from its 0 to 52.
            (2) STEADY STATE: (Cref, Tref) sustained at (2, 373.1).
            (3) STEADY STATE: (Cref, Tref) sustained at (8.57, 311.3).
            (4) Transition from (Cref, Tref) of (8.57, 311.3) to (2, 373.1), from its 22 to 74.
        
        noise_percentage: Noise value to apply to states/actions.
            int[0, 1]

        step_time: Step time in between actions.
            float(0.5, 1, 1.5)

        transition_start: Time (in seconds) at which transition will start.
            int[0, 45]

        edo_solver_n_its: n iterations to resolve Ordinary Differential Equation.
            float(0.5, 1, 1.5)
        """

        # Default initialization values
        self.Cref_signal: float = 4
        self.noise_percentage: float = 0
        self.step_time: float = Δt_sim
        self.transition_start: float = 11
        self.edo_solver_n_its: int = 2

        # Config vars received
        self.config = config
        if "Cref_signal" in config.keys():
            self.Cref_signal = config["Cref_signal"]
        if "noise_percentage" in config.keys():
            self.noise_percentage = config["noise_percentage"]
        if "step_time" in config.keys():
            self.step_time = config["step_time"]
        if "transition_start" in config.keys():
            self.transition_start = config["transition_start"]
        if "edo_solver_n_its" in config.keys():
            self.edo_solver_n_its = config["edo_solver_n_its"]


        # Update episode number, and restart iteration count.
        if self.log_data:
            self.sim_logger.new_episode()


        # Default initial conditions
        Ca0: float = 8.5698     #kmol/m3
        T0: float = 311.2639    #K
        Tc0: float = 292        #K

        # Initialize environment conditions -- overwritten later based on Cref_signal.
        self.Cr = Ca0
        self.Tr = T0
        self.Tc = Tc0

        # Initialize auxiliary variables.
        # Action parsed from the brain.
        self.ΔTc = 0
        # Max considered transition time (the simulation cannot run further).
        self.max_trans_time = max_simulation_time
        # Initialize current simulation time.
        self.it_time = 0


        ## INITIALIZE ENVIRONMENT VARIABLES BASED ON VALUE OF Cref_signal.

        # TODO: Do we really need Cref_signal == 0?
        # Declare initial conditions for current signal selection.
        if self.Cref_signal == 0:
            self.Cref = 0
            self.Tref = 0
            # TODO: What do we do with initialization values when Cref_signal == 0?
            self.Cr = 8.5698
            self.Tr = 311.2612
            self.Tc = 292
        
        # Transition from (Cref, Tref) of (8.57, 311.3) to (2, 373.1).
        # Declare initial conditions for current signal selection.
        elif self.Cref_signal == 1 \
             or self.Cref_signal == 4:
            self.Cr = 8.5698
            self.Tr = 311.2612
            self.Tc = 292
            self.Cref = self.Cr
            self.Tref = self.Tr
        
        # STEADY STATE: (Cref, Tref) sustained at (2, 373.1).
        # Declare initial conditions for current signal selection.
        elif self.Cref_signal == 2:
            self.Cr = 2
            self.Tr = 373.1311
            self.Tc = 0 # TODO: Update correct value of coolant temp.
            self.Cref = self.Cr
            self.Tref = self.Tr
        
        # STEADY STATE: (Cref, Tref) sustained at (8.57, 311.3).
        # Declare initial conditions for current signal selection.
        elif self.Cref_signal == 3:
            self.Cr = 8.5698
            self.Tr = 311.2612
            self.Tc = 292
            self.Cref = self.Cr
            self.Tref = self.Tr

        # Define step to introduce to states based on noise_percentage.
        C_max_range = (8.5698 - 2)
        T_max_range = ( 373.1311 - 311.2612)
        error_var = self.noise_percentage
        Cr_error = error_var * random.uniform(-C_max_range, C_max_range)
        Tr_error = error_var * random.uniform(-T_max_range, T_max_range)

        self.Tr_no_noise = self.Tr     # Temperature of the reactor's output, clean (without noise introduced).
        self.Cr_no_noise = self.Cr     # Concentration of the reactor's output, clean (without noise introduced).
        # Add noise for inputs to be read by the brain, or selected control.
        self.Tr += Tr_error     # Tr - Temperature of the reactor's output.
        self.Cr += Cr_error     # Cr - Concentration of the reactor's output.

        # Create render vectors
        self.Cr_vec = [self.Cr]
        self.Tr_vec = [self.Tr]
        self.Cref_vec = [self.Cref]
        self.Tref_vec = [self.Tref]
        self.Tc_vec = [self.Tc]


    def step(self, action: Dict[str, Any]):
        """Step through the environment.

        Parameters
        ----------
        action : Dict[str, Any]
            Control/action to iterate in the environment
        """

        Tc_adjust = float(action["Tc_adjust"])

        # Log iterations at every episode step.
        if self.log_data:
            self.sim_logger.log_iterations(state=self.get_state(),
                                           action=action,
                                           config=self.config)


        # Transition from (Cref, Tref) of (8.57, 311.3) to (2, 373.1).
        if self.Cref_signal == 1 \
            or self.Cref_signal == 4:

            # Select the transient data desired.
            p1 = int(self.transition_start/self.step_time)
            p2 = p1 + int(26/self.step_time)
            C_sched = interpolate.interp1d([0,p1,p2,self.max_trans_time], [8.57,8.57,2,2])
            T_sched = interpolate.interp1d([0,p1,p2,self.max_trans_time], [311.2612,311.2612,373.1311,373.1311])
            
            # Store the current iteration in auxiliary variable.
            k = self.it_time
            if self.Cref_signal == 1:
                # Update for Cref_signal==1, so transition starts right away.
                k = self.it_time + p1

            # Define the reference value for current iteration.
            self.Cref = float(C_sched(k))
            self.Tref = float(T_sched(k))
        
        # Update the latest stored  action received.
        self.ΔTc = Tc_adjust
        
        # Define step to introduce to states based on noise_percentage.
        C_max_range = (8.5698 - 2)
        T_max_range = ( 373.1311 - 311.2612)
        error_var = self.noise_percentage
        Cr_error = error_var * random.uniform(-C_max_range, C_max_range)
        Tr_error = error_var * random.uniform(-T_max_range, T_max_range)

        # Call the CSTR solver.
        model = CSTR_Solver(Tr = self.Tr_no_noise,
                            Cr = self.Cr_no_noise,
                            Tc = self.Tc,
                            ΔTc = self.ΔTc,
                            step_time = self.step_time,
                            edo_solver_n_its = self.edo_solver_n_its,
                            debug=self.debug)

        # EXTRACT UPDATED VALUES FROM SOLVER.    
        #self.Tc += self.ΔTc
        self.Tc = model.Tc              # Tc - Temperature of the coolant.
        self.Tr_no_noise = model.Tr     # Temperature of the reactor's output, clean (without noise introduced).
        self.Cr_no_noise = model.Cr     # Concentration of the reactor's output, clean (without noise introduced).
        # Add noise for inputs to be read by the brain, or selected control.
        self.Tr = self.Tr_no_noise + Tr_error   # Tr - Temperature of the reactor's output.
        self.Cr = self.Cr_no_noise + Cr_error   # Cr - Concentration of the reactor's output.

        # Increase the current iteration time by the stepping time.
        self.it_time += self.step_time

        # Update render vectors
        self.Cr_vec.append(self.Cr)
        self.Tr_vec.append(self.Tr)
        self.Cref_vec.append(self.Cref)
        self.Tref_vec.append(self.Tref)
        self.Tc_vec.append(self.Tc)

        # RENDER
        if self.render:
            self.render_f()


    def random_step(self) -> None:
        #self.step(action.get("Tc_adjust"))
        self.step(np.random.randint(-10,10))
        

    def get_state(self):
        return {
            "Cr_no_noise": self.Cr_no_noise,      # Concentration at the reactor's output, without any noise introduced (kmol/m3).
            "Tr_no_noise": self.Tr_no_noise,      # Temperature at the reactor's output, without any noise introduced (Kelvin).
            "Cr": self.Cr,         # Concentration at the reactor's output (kmol/m3).
            "Tr": self.Tr,         # Temperature at the reactor's output (Kelvin).
            "Tc": self.Tc,      # Temperature of the coolant (Kelvin).
            "Cref": self.Cref,  # Reference concentration desired by the operators at reactor's output (kmol/m3).
            "Tref": self.Tref,  # Reference temperature desired by the operators at reactor's output (Kelvin).
        }

    def halted(self) -> bool:
        try:
            if self.Tr >= thermal_runaway:
                raise ValueError("#### REACTOR HAS REACHED THERMAL RUNAWAY !! The simulation is forced to restart. ###")
            elif self.Cr <= 0:
                raise ValueError("#### REACTOR CONCENTRATION IS BELOW ZERO !! The simulation is forced to restart. ###")
            elif self.ΔTc > 10 or self.ΔTc < -10 :
                raise ValueError("#### PHYSICAL LIMITATION REACHED FOR DTc !! ###")
            else:
                return False
        except Exception:
            print(traceback.format_exc())
            print("Execution continues, sim needs to be reset to continue running.")
            return True
    

    def render_f(self):
        """Render status of the simulation.
        """
        
        self.its = int(self.it_time/self.step_time)
        t_vec = np.linspace(0, self.it_time, self.its+1)

        plt.clf()
        
        # Plot coolant temperature over time.
        plt.subplot(3,1,1)
        plt.plot(t_vec[0:self.its], self.Tc_vec[0:self.its], 'k.-', lw=2)
        plt.ylabel('Cooling Tc (K)')
        plt.legend(['Jacket Temperature'], loc='best')

        # Plot coolant concentration and setpoints over time.
        plt.subplot(3,1,2)
        plt.plot(t_vec[0:self.its], self.Cr_vec[0:self.its], 'b.-', lw=3, label=r'$C_{meas}$')
        plt.plot(t_vec[0:self.its], self.Cref_vec[0:self.its], 'k--', lw=2, label=r'$C_{sp}$')
        plt.ylabel('Ca (mol/L)')
        plt.legend(['Reactor Concentration','Concentration Setpoint'], loc='best')

        # Plot coolant temperature and setpoints over time.
        plt.subplot(3,1,3)
        plt.plot(t_vec[0:self.its], self.Tr_vec[0:self.its], 'b.-', lw=3, label=r'$T_{meas}$')
        plt.plot(t_vec[0:self.its], self.Tref_vec[0:self.its], 'k--', lw=2, label=r'$T_{sp}$')
        plt.plot(t_vec[0:self.its], [400 for x in range(0,self.its)], 'r--',lw=1)
        plt.ylabel('T (K)')
        plt.xlabel('Time (min)')
        plt.legend(['Temperature Setpoint','Reactor Temperature'], loc='best')

        # Plot and hold.
        plt.draw()
        plt.pause(0.001)


def main():

    # values in `.env`, if they exist, take priority over environment variables
    cstr_sim = CSTRSimulation()
    cstr_sim.reset()
    state = cstr_sim.get_state()
    T_list = []
    Tc_list = []
    Ca_list = []
    Cref_list = []
    Tref_list = []
    Ca_error = []
    Tref_error = []
    
    # Run a full episode with random actions.
    time = 90
    for k in range(time):
        if cstr_sim.halted():
            break
        
        Cref_list.append(cstr_sim.Cref)
        Tref_list.append(cstr_sim.Tref)
        
        cstr_sim.random_step()
        state = cstr_sim.get_state()
        
        error = (cstr_sim.Cr - cstr_sim.Cref)**2
        Ca_error.append(error)
        error = (cstr_sim.Tr - cstr_sim.Tref)**2
        Tref_error.append(error)
        
        T_list.append(state['Tr'])
        Tc_list.append(state['Tc'])
        Ca_list.append(state['Cr'])

    Ca_RMS = math.sqrt(np.average(Ca_error))
    Tref_RMS = math.sqrt(np.average(Tref_error))
    print("Ca RMF: ", Ca_RMS)
    print("Tr RMF: ", Tref_RMS)

    fig, ax = plt.subplots(3, sharex=True, figsize=(16,12))
    ax[0].plot([i for i in range(len(T_list))], T_list)
    ax[0].plot([i for i in range(len(Tref_list))], Tref_list,'r--')
    ax[1].plot([i for i in range(len(Tc_list))], Tc_list)
    ax[2].plot([i for i in range(len(Ca_list))], Ca_list)
    ax[2].plot([i for i in range(len(Cref_list))], Cref_list,'r--')

    ax[0].set_ylabel('Tr (K)')
    ax[1].set_ylabel('Tc (K)')
    ax[2].set_ylabel('Cr (kmol/m3)')
    plt.show()


if __name__ == "__main__":
    main()
