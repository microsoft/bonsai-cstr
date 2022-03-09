%% Run the sample with Bonsai brain
% This script can be run once you have trained, exported, and are locally
% running a brain via Docker (default port 5000)

% This script will run the following 2 scenarios:
% 1: Using the exported Bonsai brain with 0% noise
% 2: Using the exported Bonsai brain with noise (5% default)

clear;  clc;

%% Initialize Workspace
bonsaiExportConnect
init_vars 

%% Brain Workspace Setup
mdl = 'CSTR_Bonsai';
load_system(mdl);
set_param(mdl, 'FastRestart', 'off');
open_system(mdl)

%% SCENARIO 1: Run Brain with 0% noise noise

% Run simulation
sim('CSTR_Bonsai');

%% Save simulation output
plot_results(tout, simout, 'Brain with 0% noise');

%% SCENARIO 2: Run Brain with 5% noise

noise = 5;
conc_noise = abs(CrEQ(1)-CrEQ(5))*noise/100.0;
temp_noise = abs(TrEQ(1)-TrEQ(5))*noise/100.0;

% Run simulation
sim('CSTR_Bonsai');

%%
plot_results(tout, simout, ['Brain with ',num2str(noise),'% noise']);
