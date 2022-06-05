from dataclasses import dataclass
import math
from math import exp
import numpy as np
from scipy.integrate import odeint

π = math.pi

@dataclass
class CSTRModel:

    T: float  # Kelvin
    Tc: float  # Kelvin
    Ca: float #kmol/m3
    ΔTc: float
    ΔT: float = 0  # Kelvin
    ΔCa: float = 0 #kmol/m3
    
    

    #constants
    F: float = 1 #Volumetric flow rate (m3/h)
    V: float = 1 #Reactor volume (m3)
    k0: float = 34930800 #Pre-exponential nonthermal factor (1/h)
    E: float = 11843 #Activation energy per mole (kcal/kmol)
    R: float = 1.98588 #1.985875 #Boltzmann's ideal gas constant (kcal/(kmol·K))
    ΔH: float = -5960 #Heat of reaction per mole kcal/kmol
    phoCp: float = 500 #Density multiplied by heat capacity (kcal/(m3·K))
    UA: float = 150 #Overall heat transfer coefficient multiplied by tank area (kcal/(K·h))
    Cafin: float = 10 #kmol/m3
    Tf: float = 298.2 #K

    def __post_init__(self):

        #self.ΔT =  (self.F/self.V *(self.Tf-self.T)) - ((self.ΔH/self.phoCp)*(self.k0 * exp(-self.E/(self.R*self.T))*self.Ca)) - ((self.UA /(self.phoCp*self.V)) *(self.T-self.Tc))
        #self.T += self.ΔT

        #self.ΔCa = (self.F/self.V * (self.Cafin - self.Ca)) - (self.k0 * exp(-self.E/(self.R*self.T))*self.Ca)

        def model(z, t, u):
            x = z[0]
            y = z[1]
            dxdt = (self.F/self.V * (self.Cafin - x)) - (self.k0 * exp(-self.E/(self.R*y))*x)
            dydt =  (self.F/self.V *(self.Tf-y)) - ((self.ΔH/self.phoCp)*(self.k0 * exp(-self.E/(self.R*y))*x)) - ((self.UA /(self.phoCp*self.V)) *(y - self.Tc + u))

            dzdt = [dxdt,dydt]
            return dzdt

        #initial cond
        z0 = [self.Ca, self.T]
        n = 3 #3 4
        t = np.linspace(0,1,n)
        #input
        #u = [0,self.ΔTc]
        u = np.zeros(n)
        u[0] = self.ΔTc #-1 0

        #solution
        x = np.empty_like(t)
        y = np.empty_like(t)

        x[0] = z0[0]
        y[0] = z0[1]

        #solve ODE
        for i in range(1,n):
            tspan = [t[i-1], t[i]]
            z = odeint(model, z0, tspan, args=(u[i],))
            x[i] = z[1][0]
            y[i] = z[1][1]
            z0 = z[1]
            
        self.Ca = x[1]
        self.T = y[1]
        self.Tc += self.ΔTc

    def run_sim(self):

        def model(z, t, u):
            x = z[0]
            y = z[1]
            dxdt = (self.F/self.V * (self.Cafin - x)) - (self.k0 * exp(-self.E/(self.R*y))*x)
            dydt =  (self.F/self.V *(self.Tf-y)) - ((self.ΔH/self.phoCp)*(self.k0 * exp(-self.E/(self.R*y))*x)) - ((self.UA /(self.phoCp*self.V)) *(y - self.Tc + u))

            dzdt = [dxdt,dydt]
            return dzdt

        #initial cond
        z0 = [self.Ca, self.T]
        n = 3 #3 4
        t = np.linspace(0,1,n)
        #input
        #u = [0,self.ΔTc]
        u = np.zeros(n)
        u[0] = self.ΔTc #-1 0

        #solution
        x = np.empty_like(t)
        y = np.empty_like(t)

        x[0] = z0[0]
        y[0] = z0[1]

        #solve ODE
        for i in range(1,n):
            tspan = [t[i-1], t[i]]
            z = odeint(model, z0, tspan, args=(u[i],))
            x[i] = z[1][0]
            y[i] = z[1][1]
            z0 = z[1]
            
        self.Ca = x[1]
        self.T = y[1]
        self.Tc += self.ΔTc
        
        
            
            

        
        

