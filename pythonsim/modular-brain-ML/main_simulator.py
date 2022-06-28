import json
import os
import random
import ast
from scipy import interpolate
import math
import pandas as pd
import pickle
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from sim import cstr_model as cstr

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
        noise: float = 0,
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

        self.Cref = 8.5698
        self.Tref = 311.2612

        self.noise = noise

        self.constraint = 'ml' #simulator or ml or None

        self.y = 0
        self.thermal_run = 0

        if self.constraint == 'ml':
            self.ml_model = loaded_model = pickle.load(open('ml_predict_temperature.pkl', 'rb'))

    def episode_start(self) -> None:
        self.reset()

    def step(self):
        error_var = self.noise #system noise %
        σ_max1 = error_var * (8.5698 - 2)
        σ_max2 = error_var * ( 373.1311 - 311.2612)
        
        σ_Ca = random.uniform(-σ_max1, σ_max1)
        σ_T = random.uniform(-σ_max2, σ_max2)
        mu = 0

        #Tc
        y=0
        self.y = 0
        if self.constraint == 'ml' and self.T >= 340:
            X = [[self.Ca, self.T,self.Tc,self.ΔTc]]
            y = self.ml_model.predict(X)[0]
            #print(self.ml_model.predict_proba(X))
            if self.ml_model.predict_proba(X)[0][1] >= 0.3:
                y = 1
                self.y = 1

        model = cstr.CSTRModel(T = self.T, Ca = self.Ca, Tc = self.Tc, ΔTc = self.ΔTc)
    
        #Tc
        self.Tc += self.ΔTc

        #Tr
        self.T = model.T + σ_T

        #Ca
        self.Ca = model.Ca + σ_Ca

        #Constraints - ML
        if self.constraint == 'ml': 
            if y == 1 :
                print('ML action')
                new_ΔTc = self.ΔTc
                model2 = cstr.CSTRModel(T = self.T, Ca = self.Ca, Tc = self.Tc, ΔTc = new_ΔTc)
                while (new_ΔTc <= 10 and new_ΔTc >= -10):
                    #reduce in 10%
                    new_ΔTc -= 0.1 * abs(self.ΔTc) * np.sign(self.ΔTc)
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
            
        

    def episode_step(self,ΔTc ) -> None:
        #conect to Bonsai Brain - Connect to Modular Brain 
        payload = self.get_state()
        url = "http://localhost:5000/v1/prediction"
        try:
            r = ast.literal_eval(requests.post(url, data=json.dumps(payload)).text)
            ΔTc = r["Tc_adjust"]
        except:
            ΔTc = 0
            print("Error to get brain value")
        
        self.ΔTc = ΔTc
        self.step()

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
            self.thermal_run = 1
            return True
        elif self.Ca < 0:
            print("#### CONCENTRATION BELOW ZERO !! ###")
            return True
        elif self.ΔTc > 10 or self.ΔTc < -10 :
            print("#### PHYSICAL LIMITATION REACHED FOR DTc !! ###")
            return True
        else:
            return False


def main(graphics, noise):
    try:
        df_train = pd.read_csv('cstr_simulator_data.csv')
    except:
        df_train = pd.DataFrame()

    cstr_sim = CSTRSimulation()

    cstr_sim.reset(noise=noise)
    state = cstr_sim.get_state()
    
    T_list = []
    Tc_list = []
    Ca_list = []
    Cref_list = []
    Tref_list = []
    Ca_error = []
    Tref_error = []
    ML_list = []
        
    time = 90 #45
    graphics = graphics
    if graphics:
        plt.figure(figsize=(10,7))
        plt.ion()
    
    for k in range(time):
        #break the simulation for Thermal runaway
        if cstr_sim.halted():
            break

        df_t = pd.DataFrame([[cstr_sim.Ca,cstr_sim.T,cstr_sim.Tc]], columns = ['Ca0','T0','Tc0'])
        
        #Generate Setpoints
        p1 = 22 #22 10
        p2 = 74 #74 36
        ceq = [8.57,6.9275,5.2850,3.6425,2]
        teq = [311.2612,327.9968,341.1084,354.7246,373.1311]
        C = interpolate.interp1d([0,p1,p2,time], [8.57,8.57,2,2])
        cstr_sim.Cref = float(C(k))

        T_ = interpolate.interp1d([0,p1,p2,time], [311.2612,311.2612,373.1311,373.1311])
        cstr_sim.Tref = float(T_(k))
            
        Cref_list.append(cstr_sim.Cref)
        Tref_list.append(cstr_sim.Tref)
        
        cstr_sim.episode_step(cstr_sim.ΔTc)
        state = cstr_sim.get_state()
     
        error = (cstr_sim.Ca - cstr_sim.Cref)**2
        Ca_error.append(error)
        error = (cstr_sim.T - cstr_sim.Tref)**2
        Tref_error.append(error)

        #generate dataframe
        df_t['date'] = pd.to_datetime('now')
        df_t['sim_time'] = k
        df_t['simulation'] = 0 #add simulation
        df_t['Ca'] = cstr_sim.Ca
        df_t['T'] = cstr_sim.T
        df_t['Tref'] = cstr_sim.Tref
        df_t['Cref'] = cstr_sim.Cref
        df_t['Tc'] = cstr_sim.Tc
        df_t['dTc'] = cstr_sim.ΔTc
        df_t['noise'] = cstr_sim.noise
        df_train = df_train.append(df_t)
        
        T_list.append(state['Tr'])
        Tc_list.append(state['Tc'])
        Ca_list.append(state['Cr'])

        if graphics:
            plt.clf()

            if cstr_sim.y == 1:
                ML_list.append(k/2)
                
            plt.subplot(3,1,1)
            plt.plot([i/2 for i in range(len(Tc_list))],Tc_list,'k.-',lw=2)
            plt.ylabel('Cooling Tc (K)')
            plt.legend(['Jacket Temperature'],loc='best')
            for kx in ML_list:
                plt.axvspan(kx, kx-1, facecolor='r',alpha=0.8, label='ML actuation')
            lg = True
            if len(ML_list) > 0 and lg == True:
                plt.legend()
                lg = False
            

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
    thermal_runs = []
    tmax = 100 #simulations
    noise = 0.1
    for j in range(tmax):
        Ca_RMS,Tref_RMS,thermal_run = main(False, noise=noise)
        CA_l.append(Ca_RMS)
        Tref_l.append(Tref_RMS)
        thermal_runs.append(thermal_run)

    print("CaRMS mean: ", np.mean(CA_l), "+- ", np.std(CA_l))
    print("TrRMS mean: ", np.mean(Tref_l), "+- ", np.std(Tref_l))
    print("Thermal Runaways: ", (np.sum(thermal_runs)/len(thermal_runs))*100, ' %')

    #generate dataframe
    df_train = pd.read_csv(r'..\results-spec.csv')
    df_t = pd.DataFrame()
    df_t['date'] = [pd.to_datetime('now')]
    df_t['model'] = ['bonsai_multi_brain_ML']
    df_t['runs'] = [tmax]
    df_t['noise'] = [noise]
    df_t['CaRMS_mu'] = [np.mean(CA_l)]
    df_t['CaRMS_sigma'] = [np.std(CA_l)]
    df_t['TrRMS_mu'] = [np.mean(Tref_l)]
    df_t['TrRMS_sigma'] = [np.std(Tref_l)]
    df_t['runaway_pct'] = [(np.sum(thermal_runs)/len(thermal_runs))]

    df_train = df_train.append(df_t)

    df_train.to_csv(r'..\results-spec.csv', index=False)




