# Continuous-stirred Tank Reactor (CSTR) python simulator with Benchmarks

[Project Bonsai](https://aka.ms/bonsai) code sample demonstrating
chemical process optimization in a continuously-stirred tank reactor
(CSTR). Efficient control of an exothermic, non-linear chemical reaction
with CSTR is a benchmark in which to compare PID, MPC and Bonsai brains.

The chemical process here considers a transition from low to high
conversion rate (high to low residual concentration) in a single first-order exothermic and irreversible chemical reaction A -> B, with the follow assumptions:

* Perfectly mixed vessel
* The inlet stream of reagent A enters the tank at a constant volumetric rate
* The product stream B exits continuously at the same volumetric rate
* Liquid density is constant
* The volume of reacting liquid is constant

## Software Prerequisites

* Docker
* Python >= 3.7.4
* Miniconda


## Getting Set Up

This section will show the steps to use the CSTR Python simulator in the Bonsai Platform.

### 1.Create your environment for MiniConda

install miniforge (Miniconda from condaforge)
```shell
conda env create -f environment.yml
```
test bonsai-training-interface locally (p random)
nonlinear-mpc run (check last 3 lines)
linear-mpc run (check last 3 lines)

### 2. Import your simulator to ACR and Bonsai

#### Build the docker image
Open your terminal and go to the bonsai-training-interface folder

Build your docker image using the Dockerfile

```shell
docker build -t cstr_sim -f Dockerfile ./
```

#### Import simulator

Login to your ACR account 

```shell
docker login <Registry>.azurecr.io
```

Tag your image

```shell
docker tag cstr_sim <Registry>.azurecr.io/cstr_sim:v1
```

Push to your ACR

```shell
docker push <Registry>.azurecr.io/cstr_sim:v1
```

Import the simulator in Bonsai Platform
Click on +Add sim > Other > "in the ACR path put the name of the image

Click on add new sim
![Add new sim](img/add_sim.JPG)

Choose 'other sim'
![Choose other sim](img/other_sim.JPG)

Import from your ACR to Bonsai Env and click on 'Create simulator'
![Import simulator](img/import_sim.JPG)

After this will just need to create a new brain and train it. 
You can use the inkling files .ink from Monolithic and Modular foldres to start training your new brain.

### Extra: Run Unmanaged Simulator Locally
You can run your simulator locally with Bonsai, without send it to ACR.
After building the docker image you just need to:

1 - Run the docker image and connect to your workspace : 
docker run --rm -it -e SIM_ACCESS_KEY= <YOUR_SIM_ACCESS_KEY> -e SIM_API_HOST="https://api.bons.ai" -e SIM_WORKSPACE=<YOUR_SIM_WORKSPACE> cstr_sim

2 - You have to see these messages in your Terminal before continue: Registering Sim > Registered. > Received event: Idle

In the Bonsai Platform:
3 - Create a brain: Click on +Create Brain > Paste the ink code for the monolithic brain there
4 - Train your brain using the sim: Click on train and choose the "Unmanaged Simulator"


## Sim configs

### Actions (Manipulated Variables)

Bare minimum for the sim (all units are continuous):

| Action | Range      | Units    |
|--------|------------|----------|
| dTc    | [-10, 10]  | [Kelvin] |

Final set for **Bonsai training**:

- Performance improved when making the brain learn the per-timestep adjustment to apply to previous dTc.
- Thus, we maintained control to be dTc_adjust, and added an accumulator on sim side.

| Action     | Continuous Value | Units        |
| --------   | ------------     | ----------   |
| dTc_adjust | [-5, 5]*         | [Kelvin/min] |

*Note, given an additional rule that requires keeping dTc changes at no
more than 10 Kelvins/min, we forced dTc_adjust to be on the [-5, 5]
range (for Ts=0.5min)

## States (Control Variables)

Which matches the set of Observable States used for **bonsai training**

| State | Continuous Value | Units     |
| ----- | ---------------- | -----     |
| Cr    | [0.1, 12]        | [kmol/m3] |
| Tr    | [10, 800]        | [Kelvin]  |
| Tc    | [10, 800]        | [Kelvin]  |
| Cref  | [2, 8.57]        | [kmol/m3] |
| Tref  | [311.2, 373.1]   | [Kelvin] |

> Note, .ink file defines ranges higher than the ones shown here. That
> is made in purpose since the brain will try to explore, and thus will
> hit extreme limits in doing so.

`Tref` was removed as observable state since brain to simplify brain's
training. With Bonsai's solution we don't need `Tref` to be able to drive
the concentration linearly from one point to the next.


## Constraints

* `-10 < Tc < 10` degrees / min
* `Tr < 400` to prevent thermal runaway
