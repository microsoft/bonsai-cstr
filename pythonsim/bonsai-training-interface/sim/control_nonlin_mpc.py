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

from sim.cstr_solver import CSTR_Solver

# Import do_mpc package:
import do_mpc


# time step (seconds) between state updates
Δt = 1

π = math.pi

def non_lin_mpc(noise, CrSP, Cr0, T0, Tc0):


    # Call the CSTR solver for mpc modeling.
    solver = CSTR_Solver(Tr = T0,
                         Cr = Cr0,
                         Tc = Tc0,
                         ΔTc = 0,
                         step_time = Δt,
                         edo_solver_n_its = 1,
                         debug=False)
        
    #MPC MODEL
    model_type = 'continuous' # either 'discrete' or 'continuous'
    model = do_mpc.model.Model(model_type)
    
    # State - Environment variables CV
    Cr = model.set_variable(var_type='_x', var_name='Cr', shape=(1,1)) # Concentration
    Tr = model.set_variable(var_type='_x', var_name='Tr', shape=(1,1)) # Temperature

    # define measurements:
    model.set_meas('Cr', Cr, meas_noise=True)
    model.set_meas('Tr', Tr, meas_noise=True)

    # Input - Manipulated Variable MV
    Tc = model.set_variable(var_type='_u', var_name='Tc') # Coolant temperature

    # Non-fixed Time Varying parameters:
    Cref = model.set_variable(var_type='_tvp', var_name='Cref')
    Tref = model.set_variable(var_type='_tvp', var_name='Tref')

    # Process Dynamics Model
    model.set_rhs('Cr', solver.model_Cr(Cr, Tr) )
    model.set_rhs('Tr', solver.model_Tr(Cr, Tr, Tc) )

    # Build the model
    model.setup()

    # SETUP CONTROLLER
    mpc = do_mpc.controller.MPC(model)
    setup_mpc = {
        'n_horizon': 20,
        'n_robust': 1,
        'open_loop': 0,
        #'t_step': 0.1, #<version NLMM.py>
        't_step': Δt,
        'store_full_solution': True,
        # Use MA27 linear solver in ipopt for faster calculations:
        #'nlpsol_opts': {'ipopt.linear_solver': 'MA27'} #<version NLMM.py>
    }

    mpc.set_param(**setup_mpc)
    # scaling variables
    mpc.scaling['_x', 'Tr'] = 100
    mpc.scaling['_u', 'Tc'] = 100
    #mpc.scaling['_u', 'ω_s'] = 1

    # SETUP OBJECTIVE - COST FUNCTION
    _x = model.x
    _tvp = model.tvp
    _u = model.u #<version NLMM.py>
    # <version cstr_mpc_simulator.py (CMS.py)>
    #mterm = ((_x['Cr'] - _tvp['Cref']))**2 # terminal cost
    #lterm = ((_x['Cr'] - _tvp['Cref']))**2 # stage cost
    # <version non_linear_mpc_model.py (NLMM.py)>
    mterm = ((_x['Cr'] - CrSP))**2 # terminal cost
    lterm = ((_x['Cr'] - CrSP))**2 # stage cost

    mpc.set_objective(mterm=mterm, lterm=lterm)

    mpc.set_rterm(Tc = 1.5 * 1) # input penalty 1e-2 , 1000

    # SETUP CONSTRAINTS
    # constraints on states
    mpc.bounds['lower', '_x', 'Cr'] = 0.1
    mpc.bounds['upper', '_x', 'Cr'] = 12
    
    mpc.bounds['upper', '_x', 'Tr'] = 400
    mpc.bounds['lower', '_x', 'Tr'] = 100

    #mpc.set_nl_cons('Cr', _x['Cr'], ub=2, soft_constraint=True, penalty_term_cons=1e4) #<version NLMM.py>

    # lower bounds of the inputs
    #mpc.bounds['lower', '_u', 'dTc'] = -10 #<version NLMM.py>
    mpc.bounds['lower', '_u', 'Tc'] = 273 #273

    # upper bounds of the inputs
    #mpc.bounds['upper', '_u', 'dTc'] = 10 #<version NLMM.py>
    mpc.bounds['upper', '_u', 'Tc'] = 322

    # TIME VARYING VALUES
    # in optimizer configuration:
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
            #y = -0.2527*t_now + 11.097 #<version NLMM.py>
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
        #'integration_tool': 'cvodes', #<version NLMM.py>
        #'abstol': 1e-10, #<version NLMM.py>
        #'reltol': 1e-10, #<version NLMM.py>
        't_step': Δt
    }

    simulator.set_param(**params_simulator)

    # SETUP TV parameters
    p_num = simulator.get_p_template()
    tvp_num = simulator.get_tvp_template()

    # function for time-varying parameters
    def tvp_fun(t_now):
        return tvp_num

    # uncertain parameters
    def p_fun(t_now):
        return p_num

    simulator.set_tvp_fun(tvp_fun)
    simulator.set_p_fun(p_fun)


    simulator.setup()

    # Set the initial state of mpc, simulator and estimator:
    x0 = simulator.x0
    x0['Cr'] = Cr0
    x0['Tr'] = T0

    u0 = simulator.u0
    u0['Tc'] = Tc0
    #u0['Tc'] = TcSP #<version NLMM.py>


    mpc.x0 = x0
    simulator.x0 = x0
    estimator.x0 = x0

    mpc.u0 = u0
    simulator.u0 = u0
    estimator.u0 = u0


    mpc.set_initial_guess()

    # Simulate N steps
    Cref_vals = []
    Cr_error = []
    Tref_vals = []
    Tref_error = []
    u0_old = 0
    #<version CMS.py>
    #time = 90 #simulate 45 minutes with 0.5 minute step
    #<version NLMM.py>
    time = 1
    for k in range(time):
        if k > 1:
            u0_old = u0[0][0]
           
            
        u0 = mpc.make_step(x0) # get MPC next action
        #limit controller actions from -10 to 10 degrees Celsius
        if k > 1:
            if u0[0][0] - u0_old > 10:
                u0 = np.array([[u0_old + 10]])
            elif u0[0][0] - u0_old < -10:
                u0 = np.array([[u0_old - 10]])
        else: #<version NLMM.py>
            if u0[0][0] - Tc0 >= 10:
                u0 = np.array([[Tc0 + 10]])
            elif u0[0][0] - Tc0 <= -10:
                u0 = np.array([[Tc0 - 10]])
        
        #Add Noise
        #For random samples from N(mu,sigma**2), use: /
        #sigma * np.random.randn(...) + mu
        #error_var = 0.1
        error_var = noise
        σ_max1 = error_var * (8.5698 -2)
        σ_max2 = error_var * ( 373.1311 - 311.2612)
        mu = 0
        #v0 = mu + σ_max * np.random.randn(0, 1)
        v0 = np.array([mu + σ_max1* np.random.randn(1, 1)[0],mu + σ_max2* np.random.randn(1, 1)[0]])
        
        y_next = simulator.make_step(u0,v0=v0) # MPC

        #get all state values
        state_ops = y_next.reshape((1,2))

            # Benchmark
            Cref, Tref = self.update_references()
            
        Cref_vals.append(Cref)
        error = (y_next[0][0] - Cref)**2
        Cr_error.append(error)

        Tref_vals.append(Tref)
        error = (y_next[1][0] - Tref)**2
        Tref_error.append(error)
        
        x0 = estimator.make_step(y_next) # Simulation next step

    return u0



#print(non_lin_mpc(noise = 0, CrSP = 8.57 , Cr0 = 8.5698 , T0 = 311.2639 , Tc0 = 292))

        

