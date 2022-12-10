from sim.cstr_sim import CSTRSimulation
from typing import NamedTuple, Dict, Any, Union


class SimulatorModel:
    """
    Manages the LunarLander model that represents the simulation for this sample.
    Implements the reset and step methods required for a Bonsai simulator.
    """

    def __init__(self,
        render: bool = False,
        log_data: Union[bool, str] = False,
        debug: bool = True,):
        """ Perform global initialization here if needed before running episodes. """

        # render functionality
        self.render = render
        # logging features
        self.log_data = log_data
        # debug functionality
        self.debug = debug

        # initialize sim
        self.sim = CSTRSimulation(render = self.render,
                                  log_data = self.log_data,
                                  debug = self.debug)
        
        pass

    @property
    def sim_name(self):
        return "CSTR_sim"

    def reset(self, config) -> Dict[str, Any]:
        """ Reset any state from the previous episode and get ready to start a new episode. """
        
        # Initialize to main config variables
        # TODO: Modify to pass the dict directly.
        Cref_signal = 1
        if "Cref_signal" in config.keys():
            Cref_signal = config["Cref_signal"]
        noise_percentage = 0
        if "noise_percentage" in config.keys():
            noise_percentage = config["noise_percentage"]
        
        # Start simulation.
        self.sim.reset(Cref_signal=Cref_signal,
                       noise_percentage=noise_percentage)

        return self.sim.get_state()                        

    def step(self, action) -> Dict[str, Any]:
        """ Apply the specified action and perform one simulation step. """
        # Apply action to sim.
        # TODO: Modify to pass the dict directly.
        Tc_adjust = action["Tc_adjust"]
        self.sim.step(Tc_adjust)

        # If 'sim_halted' is set to True, that indicates that the simulator is unable to continue and
        # the episode will be discarded. This simulator sets it to False because it can always continue.
        return self.sim.get_state()

