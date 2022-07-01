import json
import os
import random
import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.animation import FuncAnimation, ImageMagickWriter
import numpy as np
import sys
from casadi import *
from scipy import interpolate

# Import do_mpc package:
import do_mpc


# time step (seconds) between state updates
Δt = 1

π = math.pi

on_spec_list = []
off_spec_list = []
Ca_RMF_list = []
Tr_RMF_list = []
thermal_run = []
df_train = pd.DataFrame()
#df_train = pd.read_csv('cstr_simulator_data.csv')

# Config
anim = True
noise = 0.05 #pct of noise
sim_total = 3 # total simulations

for idx in range(0,sim_total):
    #print(idx)
    df_op = pd.DataFrame()
    # CSTR Simulation Constants
    F = 1 #Volumetric flow rate (m3/h)
    V = 1 #Reactor volume (m3)
    k0 = 34930800 #Pre-exponential nonthermal factor (1/h)
    E = 11843 #Activation energy per mole (kcal/kmol)
    R = 1.985875 #Boltzmann's ideal gas constant (kcal/(kmol·K))
    ΔH = -5960 #Heat of reaction per mole kcal/kmol
    phoCp = 500 #Density multiplied by heat capacity (kcal/(m3·K))
    UA = 150 #Overall heat transfer coefficient multiplied by tank area (kcal/(K·h))
    Cafin = 10 #kmol/m3
    Tf = 298.2 #K    

    #initial conditions
    Ca0 = 8.5698 #kmol/m3
    T0 = 311.2639 #K
    Tc0 = 292 #K
      
    #MPC MODEL
    model_type = 'continuous' # 'discrete' or 'continuous'
    model = do_mpc.model.Model(model_type)
    
    # State - Controled variables CV
    Ca = model.set_variable(var_type='_x', var_name='Ca', shape=(1,1)) #Concentration
    T = model.set_variable(var_type='_x', var_name='T', shape=(1,1)) #Temperature

    # define measurements
    model.set_meas('Ca', Ca, meas_noise=True)
    model.set_meas('T', T, meas_noise=True)
    
    # Input - Manipulated Variable MV
    Tc = model.set_variable(var_type='_u', var_name='Tc') #cooling liquid temperature

    # Time Varying parameters
    Caf = model.set_variable(var_type='_tvp', var_name='Caf')
    Tref = model.set_variable(var_type='_tvp', var_name='Tref')

    # Process Dynamics Model
    model.set_rhs('Ca', (F/V * (Cafin - Ca)) - (k0 * exp(-E/(R*T))*Ca)  )
    model.set_rhs('T', (F/V *(Tf-T)) - ((ΔH/phoCp)*(k0 * exp(-E/(R*T))*Ca)) - ((UA /(phoCp*V)) *(T-Tc)) )
    
    # Build the model
    model.setup()

    # SETUP CONTROLLER
    mpc = do_mpc.controller.MPC(model)
    setup_mpc = {
        'n_horizon': 20,
        'n_robust': 1,
        'open_loop': 0,
        't_step': Δt,
        'store_full_solution': True,
    }

    mpc.set_param(**setup_mpc)
    # scaling variables
    mpc.scaling['_x', 'T'] = 100
    mpc.scaling['_u', 'Tc'] = 100

    #SETUP OBJECTIVE - COST FUNCTION
    _x = model.x
    _tvp = model.tvp
    mterm = ((_x['Ca'] - _tvp['Caf']))**2 # terminal cost
    lterm = ((_x['Ca'] - _tvp['Caf']))**2 # stage cost

    mpc.set_objective(mterm=mterm, lterm=lterm)

    mpc.set_rterm(Tc = 1.5 * 1) # input penalty

    # SETUP CONSTRAINTS
    # constraints on states
    mpc.bounds['lower', '_x', 'Ca'] = 0.1
    mpc.bounds['upper', '_x', 'Ca'] = 12
    mpc.bounds['upper', '_x', 'T'] = 400 
    mpc.bounds['lower', '_x', 'T'] = 100
    
    # lower bounds of the inputs
    mpc.bounds['lower', '_u', 'Tc'] = 273 #273
    
    # upper bounds of the inputs
    mpc.bounds['upper', '_u', 'Tc'] = 322

    # TIME VARYING VALUES
    tvp_temp_1 = mpc.get_tvp_template()
    tvp_temp_1['_tvp', :] = np.array([8.5698])

    tvp_temp_2 = mpc.get_tvp_template()
    tvp_temp_2['_tvp', :] = np.array([2])

    tvp_temp_3 = mpc.get_tvp_template()
    tvp_temp_3['_tvp', :] = np.array([2])
    
    def tvp_fun(t_now):
        #setpoint variables
        p1 = 22 # time to start transition
        p2 = 74 # time to end transtion
        time = 90 # simulate 45 minutes with 0.5 min timestep (90 points)
        ceq = [8.57,6.9275,5.2850,3.6425,2]
        teq = [311.2612,327.9968,341.1084,354.7246,373.1311]
        C = interpolate.interp1d([0,p1,p2,time], [8.57,8.57,2,2])
        T_ = interpolate.interp1d([0,p1,p2,time], [311.2612,311.2612,373.1311,373.1311])
        
        if t_now < p1:
            return tvp_temp_1
        elif t_now >= p1 and t_now < p2:
            y = float(C(k))
            tvp_temp_3['_tvp', :] = np.array([y])
            return tvp_temp_3
        else:
            return tvp_temp_2

    mpc.set_tvp_fun(tvp_fun)

    mpc.setup()

    #ESTIMATOR
    estimator = do_mpc.estimator.StateFeedback(model)

    #SIMULATOR
    simulator = do_mpc.simulator.Simulator(model)
    params_simulator = {
        't_step': Δt
    }

    simulator.set_param(**params_simulator)

    #SETUP TV parameters
    p_num = simulator.get_p_template()
    tvp_num = simulator.get_tvp_template()

    # function for time-varying parameters
    def tvp_fun(t_now):
        return tvp_num

    def p_fun(t_now):
        return p_num
    
    simulator.set_tvp_fun(tvp_fun)
    simulator.set_p_fun(p_fun)

    simulator.setup()

    # Set the initial state of mpc, simulator and estimator:
    x0 = simulator.x0
    x0['Ca'] = Ca0
    x0['T'] = T0

    u0 = simulator.u0
    u0['Tc'] = Tc0

    mpc.x0 = x0
    simulator.x0 = x0
    estimator.x0 = x0

    mpc.u0 = u0
    simulator.u0 = u0
    estimator.u0 = u0

    mpc.set_initial_guess()
    
    #Simulate teps
    Cref_vals = []
    Ca_error = []
    Tref_vals = []
    Tref_error = []
    T_list = []
    Tc_list = []
    Ca_list = []
    u0_old = 0
    time = 90 #simulate 45 minutes with 0.5 minute step
    for k in range(time):
        if k > 1:
            u0_old = u0[0][0]
            #generate dataset for training
            #df_t = state_ops[0]
            #df_t.append(u0[0])
            df_t = pd.DataFrame(state_ops, columns = ['Ca0','T0'])
            df_t['Tc0'] = u0[0]
            
        u0 = mpc.make_step(x0) # get MPC next action
        #limit controller actions from -10 to 10 degrees Celsius
        if k > 1:
            if u0[0][0] - u0_old > 10:
                u0 = np.array([[u0_old + 10]])
            elif u0[0][0] - u0_old < -10:
                u0 = np.array([[u0_old -10]])
            
        # Adding Noise
        error_var = noise
        σ_max1 = error_var * (8.5698 -2)
        σ_max2 = error_var * ( 373.1311 - 311.2612)
        mu = 0
        #v0 = mu + σ_max * np.random.randn(0, 1)
        v0 = np.array([mu + σ_max1* np.random.randn(1, 1)[0],mu + σ_max2* np.random.randn(1, 1)[0]])
        y_next = simulator.make_step(u0,v0=v0) # MPC

        #get all state values
        state_ops = y_next.reshape((1,2))
        #append in a table
        df_ = pd.DataFrame(state_ops, columns = ['Ca','T'])
        df_['Tc'] = u0[0]
        df_op = df_op.append(df_)
        if k > 1:
            #generate dataset
            df_t['Ca'] = df_['Ca']
            df_t['T'] = df_['T']
            df_t['Tc'] = df_['Tc']
            df_t['dTc'] = df_['Tc'] - df_t['Tc0']
            df_train = df_train.append(df_t)

        T_list.append(state_ops[0][1])
        Tc_list.append(u0[0])
        Ca_list.append(state_ops[0][0])

        if state_ops[0][1] >= 400:
            print("###########THERMAL RUNAWAY#####")
            thermal_run.append(1)
        else:
            thermal_run.append(0)

        #Benchmark
        p1 = 22 # time to start transition
        p2 = 74 # time to end transition
        ceq = [8.57,6.9275,5.2850,3.6425,2]
        teq = [311.2612,327.9968,341.1084,354.7246,373.1311]
        C = interpolate.interp1d([0,p1,p2,time], [8.57,8.57,2,2])
        T_ = interpolate.interp1d([0,p1,p2,time], [311.2612,311.2612,373.1311,373.1311])
        if k < p1:
            Cref = 8.5698
            Tref = 311.2612
        elif k >= p1 and k < p2:
            y = float(C(k))
            y2 = float(T_(k))
            Cref = y
            Tref = y2
        else:
            Cref = 2
            Tref = 373.1311
            
        Cref_vals.append(Cref)
        error = (y_next[0][0] - Cref)**2
        Ca_error.append(error) 

        Tref_vals.append(Tref)
        error = (y_next[1][0] - Tref)**2
        Tref_error.append(error)
        
        x0 = estimator.make_step(y_next) # Simulation next step

    df_op = df_op.reset_index()
    df_op['dTc'] = df_op['Tc'].diff()
    '''if df_op['T'].max() >= 400:
        print("###########THERMAL RUNAWAY#####")
        thermal_run.append(1)'''

    Ca_RMS = sqrt(np.average(Ca_error))
    Tref_RMS = sqrt(np.average(Tref_error))
    print("Ca RMF: ", Ca_RMS)
    print("Tr RMF: ", Tref_RMS)
    Ca_RMF_list.append(Ca_RMS)
    Tr_RMF_list.append(Tref_RMS)
        
    if anim == True:
        plt.subplot(3,1,1)
        plt.plot([i/2 for i in range(len(Tc_list))],Tc_list,'k.-',lw=2)
        plt.ylabel('Cooling Tc (K)')
        plt.legend(['Jacket Temperature'],loc='best')     

        plt.subplot(3,1,2)
        plt.plot([i/2 for i in range(len(Ca_list))],Ca_list,'b.-',lw=3)
        plt.plot([i/2 for i in range(len(Cref_vals))],Cref_vals,'k--',lw=2,label=r'$C_{sp}$')
        plt.ylabel('Ca (mol/L)')
        plt.legend(['Reactor Concentration','Concentration Setpoint'],loc='best')

        plt.subplot(3,1,3)
        plt.plot([i/2 for i in range(len(Tref_vals))],Tref_vals,'k--',lw=2,label=r'$T_{sp}$')
        plt.plot([i/2 for i in range(len(T_list))],T_list,'b.-',lw=3,label=r'$T_{meas}$')
        plt.plot([i/2 for i in range(len(T_list))],[400 for x in range(len(T_list))],'r--',lw=1)
        plt.ylabel('T (K)')
        plt.xlabel('Time (min)')
        plt.legend(['Temperature Setpoint','Reactor Temperature'],loc='best')

        plt.show()
        


print("CaRMS mean: ", np.mean(Ca_RMF_list), "+- ", np.std(Ca_RMF_list))
print("TRMS mean: ", np.mean(Tr_RMF_list), "+- ", np.std(Tr_RMF_list))
print("Total thermal runaway: ", (np.sum(thermal_run)/sim_total)*100, "%")

df_train.to_csv('cstr_simulator_data.csv', index=False)

#generate dataframe
df_train = pd.read_csv(r'..\results-spec.csv')
df_t = pd.DataFrame()
df_t['date'] = [pd.to_datetime('now')]
df_t['model'] = ['nonlinear_mpc']
df_t['runs'] = [sim_total]
df_t['noise'] = [noise]
df_t['CaRMS_mu'] = [np.mean(Ca_RMF_list)]
df_t['CaRMS_sigma'] = [np.std(Ca_RMF_list)]
df_t['TrRMS_mu'] = [np.mean(Tr_RMF_list)]
df_t['TrRMS_sigma'] = [np.std(Tr_RMF_list)]
df_t['runaway_pct'] = [(np.sum(thermal_run)/len(thermal_run))]

df_train = df_train.append(df_t)

df_train.to_csv(r'..\results-spec.csv', index=False)


