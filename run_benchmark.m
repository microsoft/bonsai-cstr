%% Run the sample with benchmark and brain and plot results
% This script can be run once you have trained, exported, and are locally
% running a brain.

% This script will run the following 4 simulation scenarios and plot the results:
% 1st: Gain scheduled PI without noise
% 2nd: Gain scheduled PI with noise (as configured below)
% 3rd: Brain with no noise
% 4th: Brain with noise (as configured below)

clear; close all; clc; clearvars -global

%% Set simulation configuration
bonsaiExportConnect
init_vars 


%% PI workspace setup
open_system('CSTR_PI')

%% 1. Run Gain-scheduled PI with 0% noise

% Run simulation
sim('CSTR_PI')

% Save simulation output
simout_PI = simout;
tout_PI = tout;

%% 2. Run Gain-scheduled PI with noise

% Percentage of noise to simulate
noise = 5;
conc_noise = abs(CrEQ(1)-CrEQ(5))*noise/100;
temp_noise = abs(TrEQ(1)-TrEQ(5))*noise/100;

% Run simulation
sim('CSTR_PI')

% Save simulation output
simout_PI_noise = simout;
tout_PI_noise = tout;

%% Brain Workspace Setup

init_vars

% load model and disable fast restart
mdl = 'CSTR_Bonsai';
load_system(mdl);
set_param(mdl, 'FastRestart', 'off');
open_system('CSTR_Bonsai')

%% 3. Run Brain with 0% noise noise

% Run simulation
sim('CSTR_Bonsai');

% Save simulation output
tout_b = tout;
simout_b = simout;

%% 4. Run Brain with noise

% Percentage of noise to include
noise = 5;

% Auxiliary params
conc_noise = abs(CrEQ(1)-CrEQ(5))*noise/100;
temp_noise = abs(TrEQ(1)-TrEQ(5))*noise/100;

% Run simulation
sim('CSTR_Bonsai');

% Save simulation output
tout_b_noise = tout;
simout_b_noise = simout;

%% Plot benchmark simulation results

plot_comparison(tout_b, simout_b,tout_b_noise, simout_b_noise,...
    tout_PI, simout_PI,tout_PI_noise, simout_PI_noise,noise)
