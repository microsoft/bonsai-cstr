import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
from gekko import GEKKO
from scipy import interpolate
import math
import random

from cstr_sim import CSTRSimulation


class linear_mpc:

    def __init__(self, state):

        self.remote_server = True
        self.display_mpc_vals = False
    
        # GEKKO linear MPC
        self.m = GEKKO(remote=self.remote_server)

        self.m.time = np.linspace(0, 45, num=90) #simulate 45 minutes (0.5 minute per controller action)

        # initial conditions
        self.Tc0 = state["Tc"]
        self.T0 = state["Tr_no_noise"]
        self.C0 = state["Cr_no_noise"]

        # Manipulated and Controlled Variables
        self.m.Tc = self.m.MV(value = self.Tc0, lb=273, ub=322) #mv with constraints
        self.m.T = self.m.CV(value = self.T0) #cv

        # Process dynamic model
        self.tau = self.m.Const(value = 3)
        self.Kp = self.m.Const(value = 0.75)
        self.m.Equation(self.tau * self.m.T.dt() == -(self.m.T - self.T0) + self.Kp * (self.m.Tc - self.Tc0))

        # MV tuning - Cooling Temp
        self.m.Tc.STATUS = 1
        self.m.Tc.FSTATUS = 0
        self.m.Tc.DMAXHI = 10   # constrain movement up
        self.m.Tc.DMAXLO = -10  # quick action down
        
        # CV tuning - Tr Reactor Temp
        self.m.T.STATUS = 1
        self.m.T.FSTATUS = 1
        self.m.T.SP = 311
        #m.T.UPPER = 400 #Upper constraint
        self.m.T.TR_INIT = 2
        self.m.T.TAU = 1.0 # time constant of trajectory

        self.m.options.CV_TYPE = 2  # the objective is an l2-norm (squared error)
        self.m.options.IMODE = 6    # MPC
        self.m.options.SOLVER = 3

        return
    

    def compute_action(self, state):

        # COMPUTATION OF MPC
        # insert measurement
        self.m.T.MEAS = state["Tr_no_noise"]
        # update setpoint
        self.m.T.SP = state["Tref"]

        # solve MPC
        self.m.solve(disp=self.display_mpc_vals)
        # change to a fixed starting point for trajectory
        self.m.T.TR_INIT = 2

        # retrieve new Tc values
        new_Tc = self.m.Tc.NEWVAL

        return new_Tc
