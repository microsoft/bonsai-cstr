import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
from gekko import GEKKO
from scipy import interpolate
import math
import random

#initialize variables
Ca_error = []
Tref_error = []
Cr_out = []
Tr_out = []

#simulation config
sim_max = 1 # number of simulations
error_var = 0.1 # error pct
graphics = True # live graphics 
display_mpc_vals = False
remote_server = True # use a remote server to process calculations 

for idx in range(0,sim_max):
    Tr_out_id = 0
    Cr_out_id = 0
    
    # Steady State Initial Condition
    u_ss = 280.0
    # Tf = Feed Temperature (K)
    Tf = 298.2 #K
    # Caf = Feed Concentration (kmol/m^3)
    Caf = 10 #kmol/m3

    # Steady State as initial condition for the states
    Ca_ss = 8.5698
    T_ss = 311.2612
    x0 = np.empty(2)
    x0[0] = Ca_ss
    x0[1] = T_ss

    # GEKKO linear MPC
    m = GEKKO(remote=remote_server)

    m.time = np.linspace(0, 45, num=90) #simulate 45 minutes (0.5 minute per controller action)

    # initial conditions
    Tc0 = 292
    T0 = 311
    Ca0 = 8.57

    tau = m.Const(value = 3)
    Kp = m.Const(value = 0.75)

    # Manipulated and Controlled Variables
    m.Tc = m.MV(value = Tc0,lb=273,ub=322) #mv with constraints
    m.T = m.CV(value = T_ss) #cv

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

    # CSTR model - Real dynamics
    def cstr(x,t,u,Tf,Caf):
        # Input
        # Temperature of cooling jacket (K) - MV
        Tc = u
        # Tf = Feed Temperature (K) - Constant
        Tf = 298.2 #K
        # Caf = Feed Concentration (kmol/m^3) - Constant
        Caf = 10 #kmol/m3
        
        # States
        # Concentration of A in CSTR (mol/m^3)
        Ca = x[0]
        # Temperature in CSTR (K)
        T = x[1]

        # Parameters:
        # Volumetric Flowrate (m^3/sec)
        q = 1
        # Volume of CSTR (m^3)
        V = 1
        # Density of A-B Mixture (kg/m^3) rho
        # Heat capacity of A-B Mixture (J/kg-K) Cp
        rhoCp = 500 #Density multiplied by heat capacity (kcal/(m3·K))
        # Heat of reaction for A->B (J/mol)
        mdelH = -5960 #Heat of reaction per mole kcal/kmol
        # E - Activation energy in the Arrhenius Equation (J/mol)
        # R - Universal Gas Constant = 8.31451 J/mol-K
        EoverR = 11843/1.98588
        # Pre-exponential factor (1/sec)
        k0 = 34930800 #Pre-exponential nonthermal factor (1/h)
        # U - Overall Heat Transfer Coefficient (W/m^2-K)
        # A - Area - this value is specific for the U calculation (m^2)
        UA = 150 #Overall heat transfer coefficient multiplied by tank area (kcal/(K·h))
        # reaction rate
        rA = k0*np.exp(-EoverR/T)*Ca

        # Calculate concentration derivative
        dCadt = q/V*(Caf - Ca) - rA
        # Calculate temperature derivative
        dTdt = q/V*(Tf - T) \
                - mdelH/(rhoCp)*rA \
                + ((UA/(V*rhoCp))*(Tc-T))

        # Return xdot:
        xdot = np.zeros(2)
        xdot[0] = dCadt
        xdot[1] = dTdt
        return xdot

    

    # Store results for plotting
    Ca = np.ones(len(t)) * Ca_ss
    T = np.ones(len(t)) * T_ss
    #Tsp = np.ones(len(t)) * T_ss
    Tsp = []
    Csp = []
    u = np.ones(len(t)) * u_ss

    # Set points - reference
    time = 45 #simulation time (min)
    p1 = 10 #time to start the transition
    p2 = 36 #time to finish the transition

    T_ = interpolate.interp1d([0,p1,p2,time,time+1], [311.2612,311.2612,373.1311,373.1311,373.1311])
    C = interpolate.interp1d([0,p1,p2,time, time+1], [8.57,8.57,2,2,2])

    # time Interval (min)
    t = np.linspace(0,time, time)

    # Create plot
    if graphics == True:
        plt.figure(figsize=(10,7))
        plt.ion()
        plt.show()

    # Simulate CSTR with controller
    for i in range(len(t)-1):
        # simulate one time period
        ts = [t[i],t[i+1]]
        y = odeint(cstr,x0,ts,args=(u[i],Tf,Caf))
        # retrieve measurements
        # apply noise
        σ_max1 = error_var * (8.5698 - 2)
        σ_max2 = error_var * ( 373.1311 - 311.2612)
        σ_Ca = random.uniform(-σ_max1, σ_max1)
        σ_T = random.uniform(-σ_max2, σ_max2)
        Ca[i+1] = y[-1][0] + σ_T
        T[i+1] = y[-1][1] + σ_Ca
        # insert measurement
        m.T.MEAS = T[i+1]
        # update setpoint
        m.T.SP = T_(i+1)
        Tref = T_(i+1)
        Cref = C(i+1)
        Tsp.append(Tref)
        Csp.append(Cref)
        # solve MPC
        m.solve(disp=display_mpc_vals)
        # change to a fixed starting point for trajectory
        m.T.TR_INIT = 2
        # retrieve new Tc values
        u[i+1] = m.Tc.NEWVAL
        # update initial conditions
        x0[0] = Ca[i+1]
        x0[1] = T[i+1]

        error = (x0[0] - Cref)**2
        Ca_error.append(error)
        error = (x0[1] - Tref)**2
        Tref_error.append(error)
        
        # Identify non desirable scenarios
        if x0[1] >= 400:
            print("#### THERMAL RUNAWAY !! ###")
            Tr_out_id = 1
        elif x0[0] < 0.1 or x0[0] > 12 :
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
