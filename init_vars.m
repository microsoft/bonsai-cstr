
%% SET OF CONTROLLER VARIABLES

% Load equilibrium points, used as initial conditions
load('equilibrium.mat')

% Scenario to be run - 5 scenarios: 1-based INT
% > 1: Concentration transition -->  8.57 to 2.000 over [0, 0, 36, 45]
% > 2: Concentration transition -->  8.57 to 2.000 over [0, 10, 36, 45]
% > 3: Concentration transition -->  8.57 to 2.000 over [0, 20, 46, 55]
% > 4: Concentration transition -->  8.57 to 2.000 over [0, 30, 56, 65]
% > 5: Steady state -->  8.57

Cref_signal = 2;

% Percentage of noise to include
noise_magnitude = 0/100;

% Sample time used for controller
Ts = 0.5;

% Goal is to take concentration from ~8.5 down to 2
Cr_vec = [2:.5:9]; 

% Auxiliary params
conc_noise = abs(CrEQ(1)-CrEQ(5))*noise_magnitude;
temp_noise = abs(TrEQ(1)-TrEQ(5))*noise_magnitude;
