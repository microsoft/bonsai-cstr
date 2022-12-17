from dataclasses import dataclass
import math
from math import exp
import numpy as np
from scipy.integrate import odeint

π = math.pi


@dataclass
class CSTR_Solver:

    # Problem states & actions.
    Cr: float       # Concentration at the reactor's output (kmol/m3)
    Tr: float       # Temperature at the reactor's output (Kelvin)
    Tc: float       # Temperature of the coolant (Kelvin)
    ΔTc: float      # Delta action to apply to the temperature of the coolant.


    # Running parameters
    edo_solver_n_its: int = 1      # Number of runs to perform to resolve the ODE: Ordinary Differential Equation.
    step_time: int = 1             # Step time to run the simulation for at each simulation execution.
    

    # Problem constants.
    F: float = 1 # Volumetric flow rate (m3/h)
    V: float = 1 # Reactor volume (m3)
    k0: float = 34930800    # Pre-exponential nonthermal factor (1/h)
    E: float = 11843        # Activation energy per mole (kcal/kmol)
    R: float = 1.98588  # Boltzmann's ideal gas constant (kcal/(kmol·K))
    ΔH: float = -5960   # Heat of reaction per mole kcal/kmol
    phoCp: float = 500  # Density multiplied by heat capacity (kcal/(m3·K))
    UA: float = 150     # Overall heat transfer coefficient multiplied by tank area (kcal/(K·h))
    Cafin: float = 10   # Feed Concentration (kmol/m^3)
    Tf: float = 298.2   # Feed Temperature (K)


    def __post_init__(self):
        """""
        By default, resolve the ODE right after the object is generated.
        """""
        self.run_sim()


    def run_sim(self):
        """""
        Method that queues the computation of the ODE (ordinary differential equation).
        """""

        # Setup current conditions.
        # TODO: Make this depend on the stepping time.
        # TODO: Question for Octavio: Why do we run the solver for 3 iterations? Do we know the right amount for the stepping time (0.5s VS 1s)?
        if abs(self.ΔTc) > 10:
            self.ΔTc = 10 * self.ΔTc/abs(self.ΔTc)
            raise ValueError(f"Current provided value of {self.ΔTc} exceeds the max ramp value of 10.")

        # Setup current conditions.
        z0 = [self.Cr, self.Tr]
        t = np.linspace(0, self.step_time, self.edo_solver_n_its+1)
        
        # Setup the changing conditions to the coolant temp.
        #u = [0,self.ΔTc]
        u = np.zeros(self.edo_solver_n_its+1)
        u[0] = self.ΔTc #-1 0

        # Setup output variables to store intermediate results.
        x = np.empty_like(t)
        y = np.empty_like(t)
        # Initialize the first array values to whichever current conditions.
        x[0] = z0[0]
        y[0] = z0[1]

        # Run the solver for 'n' steps to solve the ODE (Ordinary Differential Equation).
        for i in range(1,self.edo_solver_n_its+1):
            tspan = [t[i-1], t[i]]
            z = odeint(self.model, z0, tspan, args=(u[i],))
            x[i] = z[1][0]
            y[i] = z[1][1]
            z0 = z[1]
        
        # Extract the upadted values for reactor temp & conc, as well as coolant temp.
        self.Cr = x[1]
        self.Tr = y[1]
        self.Tc += self.ΔTc
    

    def model(self, z, t, u):
        """""
        Method that resolves the ODE (ordinary differential equation).
        """""
        x = z[0]  # Reactor Concentrarion
        y = z[1]  # Reactor Temperature
        
        # reaction rate
        rA = self.k0 * exp(-self.E/(self.R*y))*x

        # Calculate concentration derivative
        dxdt = (self.F/self.V * (self.Cafin - x)) - rA
        # Calculate temperature derivative
        dydt = (self.F/self.V *(self.Tf-y)) \
               - ((self.ΔH/self.phoCp)*rA) \
               - ((self.UA /(self.phoCp*self.V)) * (y - (self.Tc + u)))

        dzdt = [dxdt,dydt]
        return dzdt
            
            

        
        

