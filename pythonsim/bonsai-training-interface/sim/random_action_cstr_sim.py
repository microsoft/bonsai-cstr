import json
import os
import random
import ast
from scipy import interpolate
import math


import cstr_model as cstr

import numpy as np
import sys

import matplotlib.pyplot as plt

# time step (seconds) between state updates
Δt = 1

class CSTRSimulation():
    def reset(
        self,
        Cref_signal: float = 0,
        noise_percentage: float = 0,
        ΔTc: float = 0,
        Ca: float = 0,
        T: float = 0,
        Tc: float = 0,
        Cref: float = 0,
        Tref: float = 0,
        cnt: float = 0
    ):
        """
        CSTR model for simulation.
        """
        #initial conditions
        Ca0: float = 8.5698 #kmol/m3
        T0: float = 311.2639 #K
        Tc0: float = 292 #K
        
        self.T = T0
        self.Tc = Tc0
        self.Ca = Ca0
        self.ΔTc = 0

        self.cnt = 0

        self.Cref_signal = Cref_signal
        self.noise_percentage = noise_percentage
        
        if self.Cref_signal == 2:
            self.Cref = 2
            self.Tref = 373.1311
            self.Ca = 2
            self.T = 373.1311
        else:
            self.Cref = 8.5698
            self.Tref = 311.2612

        


    def step(self, ΔTc: float):
        if self.Cref_signal == 0:
            self.Cref = 0
            self.Tref = 0
        elif self.Cref_signal == 1:
            #update Cref an Tref
            time = 90
            p1 = 22 
            p2 = 74
            k = self.cnt+p1
            ceq = [8.57,6.9275,5.2850,3.6425,2]
            teq = [311.2612,327.9968,341.1084,354.7246,373.1311]
            C = interpolate.interp1d([0,p1,p2,time], [8.57,8.57,2,2])
            self.Cref = float(C(k))
            T_ = interpolate.interp1d([0,p1,p2,time], [311.2612,311.2612,373.1311,373.1311])
            self.Tref = float(T_(k))
        elif self.Cref_signal == 2: #steady state 1
            self.Cref = 2
            self.Tref = 373.1311
        elif self.Cref_signal == 3: #steady state 2
            self.Cref = 8.5698
            self.Tref = 311.2612
        elif self.Cref_signal == 4: #full sim
            k = self.cnt
            time = 90
            #update Cref an Tref
            p1 = 22 
            p2 = 74 
            ceq = [8.57,6.9275,5.2850,3.6425,2]
            teq = [311.2612,327.9968,341.1084,354.7246,373.1311]
            C = interpolate.interp1d([0,p1,p2,time], [8.57,8.57,2,2])
            self.Cref = float(C(k))
            T_ = interpolate.interp1d([0,p1,p2,time], [311.2612,311.2612,373.1311,373.1311])
            self.Tref = float(T_(k))
            
        self.ΔTc = ΔTc
        
        error_var = self.noise_percentage
        σ_max1 = error_var * (8.5698 - 2)
        σ_max2 = error_var * ( 373.1311 - 311.2612)

        σ_Ca = random.uniform(-σ_max1, σ_max1)
        σ_T = random.uniform(-σ_max2, σ_max2)
        mu = 0

        #calling the CSTR python model
        model = cstr.CSTRModel(T = self.T, Ca = self.Ca, Tc = self.Tc, ΔTc = self.ΔTc)

        #Tc
        self.Tc += self.ΔTc

        #Tr
        self.T = model.T + σ_T

        #Ca
        self.Ca = model.Ca + σ_Ca

        #Increase time
        self.cnt += 1

    def episode_step(self) -> None:
        #self.step(action.get("Tc_adjust"))
        #Random actions
        self.step(np.random.randint(-10,10))
        

    def get_state(self):
        return {
            "Tr": self.T,
            "Tc": self.Tc,
            "Cr": self.Ca,
            "Tref": self.Tref,
            "Cref": self.Cref,
        }

    def halted(self) -> bool:
        if self.T >= 400:
            print("#### THERMAL RUNAWAY !! ###")
            return True
        elif self.Ca < 0:
            print("#### CONCENTRATION BELOW ZERO !! ###")
            return True
        elif self.ΔTc > 10 or self.ΔTc < -10 :
            print("#### PHYSICAL LIMITATION REACHED FOR DTc !! ###")
            return True
        else:
            return False

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
    
    time = 90
    
    for k in range(time):
        if cstr_sim.halted():
            break

        #update Cref and Tref
        p1 = 22
        p2 = 74 
        ceq = [8.57,6.9275,5.2850,3.6425,2]
        teq = [311.2612,327.9968,341.1084,354.7246,373.1311]
        C = interpolate.interp1d([0,p1,p2,time], [8.57,8.57,2,2])
        cstr_sim.Cref = float(C(k))
        T_ = interpolate.interp1d([0,p1,p2,time], [311.2612,311.2612,373.1311,373.1311])
        cstr_sim.Tref = float(T_(k))
            
        Cref_list.append(cstr_sim.Cref)
        Tref_list.append(cstr_sim.Tref)
        
        #cstr_sim.episode_step(np.random.randint(-10,10))
        #cstr_sim.episode_step(cstr_sim.ΔTc)
        cstr_sim.episode_step()
        state = cstr_sim.get_state()
        
        error = (cstr_sim.Ca - cstr_sim.Cref)**2
        Ca_error.append(error)
        error = (cstr_sim.T - cstr_sim.Tref)**2
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
