import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
from gekko import GEKKO
from scipy import interpolate
import math
import random

from cstr_sim import CSTRSimulation

#initialize variables
Ca_error = []
Tref_error = []
Cr_out = []
Tr_out = []

# Debugging functionality
debug_code = True

Cr_out_per_it = []
Tr_out_per_it = []
Cref_out_per_it = []
Tref_out_per_it = []

#simulation config
sim_max = 1 # number of simulations
error_var = 0.01 # error pct
graphics = True # live graphics 
display_mpc_vals = False
remote_server = True # use a remote server to process calculations 

for idx in range(0,sim_max):
    Tr_out_id = 0
    Cr_out_id = 0
    
    cstr_sim = CSTRSimulation(debug=debug_code)
    cstr_sim.reset(config={"edo_solver_n_its": 1})
    state = cstr_sim.get_state()
    Tc_adjust = 0
    
    Tr = state["Tr"]
    Cr = state["Cr"]
    Tref = state["Tref"]
    Cref = state["Cref"]
    print(f"AUX VARS -- {Tr}, {Cr}, {Tref}, {Cref},")


    # GEKKO linear MPC
    m = GEKKO(remote=remote_server)

    m.time = np.linspace(0, 45, num=90) #simulate 45 minutes (0.5 minute per controller action)

    # initial conditions
    Tc0 = 292
    T0 = 311.2612
    Ca0 = 8.5698

    tau = m.Const(value = 3)
    Kp = m.Const(value = 0.75)

    # Manipulated and Controlled Variables
    m.Tc = m.MV(value = Tc0,lb=273,ub=322) #mv with constraints
    m.T = m.CV(value = T0) #cv

    # Process dynamic model
    m.Equation(tau * m.T.dt() == -(m.T - T0) + Kp * (m.Tc - Tc0))

    #MV tuning - Cooling Temp
    m.Tc.STATUS = 1
    m.Tc.FSTATUS = 0
    m.Tc.DMAXHI = 10   # constrain movement up
    m.Tc.DMAXLO = -10  # quick action down
    
    #CV tuning - Tr Reactor Temp
    m.T.STATUS = 1
    m.T.FSTATUS = 1
    m.T.SP = 311
    #m.T.UPPER = 400 #Upper constraint
    m.T.TR_INIT = 2
    m.T.TAU = 1.0 # time constant of trajectory

    m.options.CV_TYPE = 2 # the objective is an l2-norm (squared error)
    m.options.IMODE = 6 # MPC
    m.options.SOLVER = 3



    
    # time Interval (min)
    time = 45 #simulation time (min)
    t = np.linspace(0,time, time+1)
    
    # Store results for plotting
    Ca = np.ones(len(t)) * Ca0
    T = np.ones(len(t)) * T0
    #Tsp = np.ones(len(t)) * T_ss
    Tsp = []
    Csp = []
    u = np.ones(len(t)) * Tc0

    # Create plot
    if graphics == True:
        plt.figure(figsize=(10,7))
        plt.ion()
        plt.show()

    
    # Simulate CSTR with controller
    for i in range(time):
        # simulate one time period
        ts = [t[i],t[i+1]]
        cstr_sim.step({"Tc_adjust": Tc_adjust})
        state = cstr_sim.get_state()
        
        # Get new sim conditions
        Tr = state["Tr"]
        Cr = state["Cr"]
        Tref = state["Tref"]
        Cref = state["Cref"]

        # retrieve measurements
        # apply noise
        σ_max1 = error_var * (8.5698 - 2)
        σ_max2 = error_var * ( 373.1311 - 311.2612)
        σ_Ca = random.uniform(-σ_max1, σ_max1)
        σ_T = random.uniform(-σ_max2, σ_max2)
        # Update graph values
        Ca[i+1] = Cr #+ σ_T
        T[i+1] = Tr #+ σ_Ca

        # COMPUTATION OF MPC
        # insert measurement
        m.T.MEAS = Tr
        # update setpoint
        m.T.SP = Tref
        if debug_code:
            print(f"  --> m.T.MEAS {m.T.MEAS}, m.T.SP {m.T.SP}")
        
        Tsp.append(Tref)
        Csp.append(Cref)
        if debug_code:
            print(f"AUX VARS -- {Tr}, {Cr}, {Tref}, {Cref},")
        Cr_out_per_it.append(float(Cr))
        Tr_out_per_it.append(float(Tr))
        Cref_out_per_it.append(float(Cref))
        Tref_out_per_it.append(float(Tref))
        # solve MPC
        m.solve(disp=display_mpc_vals)
        # change to a fixed starting point for trajectory
        m.T.TR_INIT = 2
        # retrieve new Tc values
        u[i+1] = m.Tc.NEWVAL
        Tc_adjust = u[i+1]-u[i]


        error = (Cr - Cref)**2
        Ca_error.append(error)
        error = (Tr - Tref)**2
        Tref_error.append(error)
        
        # Identify non desirable scenarios
        if Tr >= 400:
            print("#### THERMAL RUNAWAY !! ###")
            Tr_out_id = 1
        elif Cr < 0.1 or Cr > 12 :
            Cr_out_id = 1
            print("#### CONCENTRATION OUT OF SPEC!! ###")

        # Plot the results
        if graphics == True:
            plt.clf()
            
            plt.subplot(3,1,1)
            plt.plot(t[0:i],u[0:i],'k.-',lw=2)
            plt.ylabel('Cooling Tc (K)')
            plt.legend(['Jacket Temperature'],loc='best')

            plt.subplot(3,1,2)
            plt.plot(t[0:i],Ca[0:i],'b.-',lw=3)
            plt.plot(t[0:i],Csp[0:i],'k--',lw=2,label=r'$C_{sp}$')
            plt.ylabel('Ca (mol/L)')
            plt.legend(['Reactor Concentration','Concentration Setpoint'],loc='best')

            plt.subplot(3,1,3)
            plt.plot(t[0:i],Tsp[0:i],'k--',lw=2,label=r'$T_{sp}$')
            plt.plot(t[0:i],T[0:i],'b.-',lw=3,label=r'$T_{meas}$')
            plt.plot(t[0:i],[400 for x in range(0,i)],'r--',lw=1)
            plt.ylabel('T (K)')
            plt.xlabel('Time (min)')
            plt.legend(['Temperature Setpoint','Reactor Temperature'],loc='best')
            plt.draw()
            plt.pause(0.001)

    Tr_out.append(Tr_out_id)
    Cr_out.append(Cr_out_id)
    plt.close()

Ca_RMS = math.sqrt(np.average(Ca_error))
Tref_RMS = math.sqrt(np.average(Tref_error))

#print results
print("Ca RMF: ", Ca_RMS , "+- ", np.std(Ca_error))
print("Tr RMF: ", Tref_RMS, "+- ", np.std(Tref_error))
print("Thermal Runaway: ", (np.sum(Cr_out)/sim_max)*100 , " %")
print("Concentration Out: ", (np.sum(Tr_out)/sim_max)*100, " %" )

#print results
print("\nCr OUT -- Cr_out_per_it: ", Cr_out_per_it)
print("\nTr OUT -- Tr_out_per_it: ", Tr_out_per_it)
print("\nCa OUT -- Cref_out_per_it: ", Cref_out_per_it)
print("\nCa OUT -- Tref_out_per_it: ", Tref_out_per_it)