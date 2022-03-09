
%% SET OF CONTROLLER VARIABLES

% Load equilibrium points, used as initial conditions
load('cstr_data.mat')

% Scenario to be run - 5 scenarios: 1-based INT
% > 1: Concentration transition -->  8.57 to 2.000 over [0, 0, 36, 45]
% > 2: Concentration transition -->  8.57 to 2.000 over [0, 10, 36, 45]
% > 3: Concentration transition -->  8.57 to 2.000 over [0, 20, 46, 55]
% > 4: Concentration transition -->  8.57 to 2.000 over [0, 30, 56, 65]
% > 5: Steady state -->  8.57

global Cref_signal;
Cref_signal = 2;

% Sample time used for controller
global Ts;
Ts = 0.5;

% Goal is to take concentration from ~8.5 down to 2
global Cr_vec;
Cr_vec = [2:.5:9]; 

global conc_noise;
global temp_noise;

conc_noise = 0;
temp_noise = 0;
