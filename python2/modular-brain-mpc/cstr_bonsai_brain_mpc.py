import json
import os
import random
import ast
from scipy import interpolate
import math
import pandas as pd
import pickle
import sys
import os

from bonsai_common import SimulatorSession, Schema
from microsoft_bonsai_api.simulator.client import BonsaiClientConfig
from microsoft_bonsai_api.simulator.generated.models import SimulatorInterface

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from sim import cstr_model as cstr
from sim import non_linear_mpc_model 

import numpy as np

import matplotlib.pyplot as plt

import requests

# time step (seconds) between state updates
Δt = 1

class CSTRSimulation():
    def reset(
        self,
        ΔTc: float = 0,
        Ca: float = 0,
        T: float = 0,
        Tc: float = 0,
        Cref: float = 0,
        Tref: float = 0,
        constraint: str = None,
    ):
        """
        CSTR model for simulation.

        constraint : Varible to turn on the constraint mode. `ml` for Machine Learning constraints
        """
        #initial conditions
        Ca0: float = 8.5698 #kmol/m3
        T0: float = 311.2639 #K
        Tc0: float = 292 #K
        
        self.T = T0
        self.Tc = Tc0
        self.Ca = Ca0
        self.ΔTc = 0

        self.Cref = 8.5698
        self.Tref = 311.2612

        self.constraint = None #simulator or ml or None

        self.thermal_run = []

        if self.constraint == 'ml':
            self.ml_model = loaded_model = pickle.load(open('ml_predict_temperature.pkl', 'rb'))

    def episode_start(self, config: Schema) -> None:
        self.reset()

    def step(self, k):
        #Get setpoints
        p1 = 22 #
        p2 = 74 #
        time = 90
        ceq = [8.57,6.9275,5.2850,3.6425,2]
        teq = [311.2612,327.9968,341.1084,354.7246,373.1311]
        C = interpolate.interp1d([0,p1,p2,time], [8.57,8.57,2,2])
        T_ = interpolate.interp1d([0,p1,p2,time], [311.2612,311.2612,373.1311,373.1311])
        CrSP = C(k)
        TcSP = T_(k)

        error_var = 0.05 #noise % into the system
        σ_max1 = error_var * (8.5698 - 2)
        σ_max2 = error_var * ( 373.1311 - 311.2612)
        
        σ_Ca = random.uniform(-σ_max1, σ_max1)
        σ_T = random.uniform(-σ_max2, σ_max2)
        mu = 0

        y=0
        if self.constraint == 'ml' and self.T >= 340:
            X = [[self.Ca, self.T,self.Tc,self.ΔTc]]
            y = self.ml_model.predict(X)[0]
            if self.ml_model.predict_proba(X)[0][1] >= 0.3:
                y = 1

        #Import MPC
        MPC_Tc = non_linear_mpc_model.non_lin_mpc(0, CrSP, self.Ca , self.T, self.Tc + self.ΔTc)
        dTc_MPC = MPC_Tc[0][0] - self.Tc
        #limit MPC actions between -10 and 10 degrees Celsius
        if dTc_MPC > 10:
            dTc_MPC = 10
        elif dTc_MPC < 10:
            dTc_MPC = -10
        self.ΔTc = dTc_MPC

        # Get state values from CSTR Dynamic Model
        model = cstr.CSTRModel(T = self.T, Ca = self.Ca, Tc = self.Tc, ΔTc = self.ΔTc)
    
        #Tc
        self.Tc += self.ΔTc

        #Tr
        self.T = model.T + σ_T

        #Ca
        self.Ca = model.Ca + σ_Ca

        #Constraints - ML model to restrict action when a Thermal Runaway scenario is detected for next state
        elif self.constraint == 'ml': 
            if y == 1 :
                new_ΔTc = self.ΔTc
                model2 = cstr.CSTRModel(T = self.T, Ca = self.Ca, Tc = self.Tc, ΔTc = new_ΔTc)
                while (new_ΔTc <= 10 and new_ΔTc >= -10):
                    #reduce in 5%
                    new_ΔTc -= 0.05 * abs(self.ΔTc) * np.sign(self.ΔTc)
                    X = [[self.Ca, self.T ,self.Tc,new_ΔTc]]
                    y = self.ml_model.predict(X)[0]
                    if self.ml_model.predict_proba(X)[0][1] >= 0.3:
                        y = 1
                    if y == 0:
                        model2.ΔTc = new_ΔTc
                        model2.run_sim()
                        break
                    
                self.ΔTc = new_ΔTc
                self.T = model2.T
                self.Ca = model2.Ca
            
        

    def episode_step(self,ΔTc, k) -> None:
        #conect to Bonsai Brain
        payload = self.get_state()
        url = "http://localhost:5000/v1/prediction"
        r = ast.literal_eval(requests.post(url, data=json.dumps(payload)).text)
        try:
            ΔTc = r["Tc_adjust"]
        except:
            ΔTc = 0
            print("Error to get brain value")
            print("response: ", r)
        
        self.ΔTc = ΔTc
        self.step(k)

    def get_state(self):
        return {
            "Tr": self.T,
            "Tc": self.Tc,
            "Cr": self.Ca,
            "Cref": self.Cref,
        }

    def halted(self) -> bool:
        if self.T >= 400:
            print("#### THERMAL RUNAWAY !! ###")
            self.thermal_run.append(1)
            return True
        elif self.Ca < 0:
            print("#### CONCENTRATION BELOW ZERO !! ###")
            return True
        elif self.ΔTc > 10 or self.ΔTc < -10 :
            print("#### PHYSICAL LIMITATION REACHED FOR DTc !! ###")
            return True
        else:
            return False

    def get_interface(self) -> SimulatorInterface:
        """Register sim interface."""

        with open("interface.json", "r") as infile:
            interface = json.load(infile)

        return SimulatorInterface(
            name=interface["name"],
            timeout=interface["timeout"],
            simulator_context=self.get_simulator_context(),
            description=interface["description"],
        )
    

def main():
    #df_train = pd.read_csv('cstr_simulator_data.csv')
    df_train = pd.DataFrame()

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
    
    graphics = True #Live graphics 
    time = 90 #simulating 45 minutes with 0.5 min per step
    if graphics:
        plt.figure(figsize=(10,7))
        plt.title("Linear MPC CSTR Control")
        plt.ion()
    
    # Start simulation
    for k in range(time):
        if cstr_sim.halted():
            break

        df_t = pd.DataFrame([[cstr_sim.Ca,cstr_sim.T,cstr_sim.Tc]], columns = ['Ca0','T0','Tc0'])
        
        #generate Setpoints
        p1 = 22 #start transition
        p2 = 74 #end transition
        ceq = [8.57,6.9275,5.2850,3.6425,2]
        teq = [311.2612,327.9968,341.1084,354.7246,373.1311]
        C = interpolate.interp1d([0,p1,p2,time], [8.57,8.57,2,2])
        cstr_sim.Cref = float(C(k))
        
        T_ = interpolate.interp1d([0,p1,p2,time], [311.2612,311.2612,373.1311,373.1311])
        cstr_sim.Tref = float(T_(k))
            
        Cref_list.append(cstr_sim.Cref)
        Tref_list.append(cstr_sim.Tref)
        
        cstr_sim.episode_step(cstr_sim.ΔTc, k)
        state = cstr_sim.get_state()
        
        #generate dataframe
        df_t['Ca'] = cstr_sim.Ca
        df_t['T'] = cstr_sim.T
        df_t['Tc'] = cstr_sim.Tc
        df_t['dTc'] = cstr_sim.ΔTc
        df_train = df_train.append(df_t)

        error = (cstr_sim.Ca - cstr_sim.Cref)**2
        Ca_error.append(error)
        error = (cstr_sim.T - cstr_sim.Tref)**2
        Tref_error.append(error)
        
        T_list.append(state['Tr'])
        Tc_list.append(state['Tc'])
        Ca_list.append(state['Cr'])

        if graphics:
            plt.clf()
                
            plt.subplot(3,1,1)
            plt.plot([i/2 for i in range(len(Tc_list))],Tc_list,'k.-',lw=2)
            plt.ylabel('Cooling Tc (K)')
            plt.legend(['Jacket Temperature'],loc='best')

            plt.subplot(3,1,2)
            plt.plot([i/2 for i in range(len(Ca_list))],Ca_list,'b.-',lw=3)
            plt.plot([i/2 for i in range(len(Cref_list))],Cref_list,'k--',lw=2,label=r'$C_{sp}$')
            plt.ylabel('Ca (mol/L)')
            plt.legend(['Reactor Concentration','Concentration Setpoint'],loc='best')

            plt.subplot(3,1,3)
            plt.plot([i/2 for i in range(len(Tref_list))],Tref_list,'k--',lw=2,label=r'$T_{sp}$')
            plt.plot([i/2 for i in range(len(T_list))],T_list,'b.-',lw=3,label=r'$T_{meas}$')
            plt.plot([i/2 for i in range(len(T_list))],[400 for x in range(len(T_list))],'r--',lw=1)
            plt.ylabel('T (K)')
            plt.xlabel('Time (min)')
            plt.legend(['Temperature Setpoint','Reactor Temperature'],loc='best')
            plt.draw()
            plt.pause(0.001)

    Ca_RMS = math.sqrt(np.average(Ca_error))
    Tref_RMS = math.sqrt(np.average(Tref_error))
    print("Ca RMF: ", Ca_RMS)
    print("Tr RMF: ", Tref_RMS)

    df_train.to_csv('cstr_simulator_data.csv', index=False)

    return Ca_RMS,Tref_RMS,cstr_sim.thermal_run


if __name__ == "__main__":
    CA_l = []
    Tref_l = []
    thermal_run_l = []

    tmax = 100 #simulations
    for j in range(tmax):
        Ca_RMS,Tref_RMS,thermal_run_ = main()
        CA_l.append(Ca_RMS)
        Tref_l.append(Tref_RMS)
        if np.sum(thermal_run_) > 0:
            thermal_run_l.append(1)
        else:
            thermal_run_l.append(0)

    print("CaRMF mean: ", np.mean(CA_l), "+- ", np.std(CA_l))
    print("TRMF mean: ", np.mean(Tref_l), "+- ", np.std(Tref_l))
    print("Thermal Runaway (%): ", np.sum(thermal_run_l)/tmax *100)


