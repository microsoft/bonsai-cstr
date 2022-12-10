"""
Fixed policies to test our sim integration with. These are intended to take
Brain states and return Brain actions.
"""

import random
from typing import Dict
import requests

global available_policy_list
available_policy_list = ["lower_Tc",
                         "increase_Tc",
                         "do_nothing"]
def chosen_policy(state, policy_name="lower_Tc"):
    """
    Apply selected user policy.
    """
    
    # Ignore the state, continuously decrease Tc.
    if policy_name == "lower_Tc":
        action = {"Tc_adjust": -10}
    # Ignore the state, continuously increase Tc.
    elif policy_name == "increase_Tc":
        action = {"Tc_adjust": 10}
    # Ignore the state, do nothing.
    elif policy_name == "do_nothing":
        action = {"Tc_adjust": 0}
    
    return action


def brain_policy(
    state: Dict[str, float], exported_brain_url: str = "http://localhost:5000"
):

    prediction_endpoint = f"{exported_brain_url}/v1/prediction"
    response = requests.get(prediction_endpoint, json=state)

    return response.json()
